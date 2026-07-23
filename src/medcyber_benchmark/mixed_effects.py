"""Prespecified explanatory mixed-model sequence and family-cluster GEE fallbacks.

The primary inference remains the paired two-way bootstrap in ``analysis.py``.
This module consumes only the three released sensitivity-row CSVs and records
every attempted explanatory specification.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import warnings
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Annotated, Any, Final, Literal

import numpy as np
import pandas as pd  # type: ignore[import-untyped]
import scipy.stats  # type: ignore[import-untyped]
import statsmodels  # type: ignore[import-untyped]
import statsmodels.api as sm  # type: ignore[import-untyped]
import statsmodels.formula.api as smf  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from statsmodels.genmod.bayes_mixed_glm import (  # type: ignore[import-untyped]
    BinomialBayesMixedGLM,
)

ANALYSIS_VERSION: Final = "mixed-effects-analysis-1.0.0"
EXPECTED_STATSMODELS_VERSION: Final = "0.14.6"
RNG_SEED: Final = 2026071901
CONDITION_PATTERN: Final = r"^[a-z][a-z0-9_]{2,127}$"

Sha256 = Annotated[
    str,
    StringConstraints(strict=True, pattern=r"^[a-f0-9]{64}$"),
]


class ContractModel(BaseModel):
    """Strict local contract used by the public sensitivity-analysis report."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        validate_assignment=True,
        str_strip_whitespace=True,
    )


class MixedEffectsAnalysisError(RuntimeError):
    """The explanatory analysis contract or write-once output failed."""


def _canonical_json_bytes(value: object, *, newline: bool = False) -> bytes:
    suffix = b"\n" if newline else b""
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        + suffix
    )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class InputFileHash(ContractModel):
    relative_path: str = Field(strict=True, min_length=1, max_length=512)
    sha256: Sha256
    size_bytes: int = Field(strict=True, ge=1)


class FitAttempt(ContractModel):
    ordinal: int = Field(strict=True, ge=1, le=8)
    specification: str = Field(strict=True, min_length=1, max_length=512)
    estimator: str = Field(strict=True, min_length=1, max_length=128)
    optimizer: str | None = Field(default=None, max_length=64)
    status: Literal["SUCCESS", "FAILED", "UNAVAILABLE"]
    converged: bool | None = None
    warning_count: int = Field(strict=True, ge=0, le=100)
    diagnostic: str = Field(strict=True, min_length=1, max_length=1024)
    diagnostic_sha256: Sha256

    @model_validator(mode="after")
    def validate_diagnostic_hash(self) -> FitAttempt:
        observed = hashlib.sha256(self.diagnostic.encode("utf-8")).hexdigest()
        if observed != str(self.diagnostic_sha256):
            raise ValueError("diagnostic SHA-256 mismatch")
        return self


class CoefficientEstimate(ContractModel):
    term: str = Field(strict=True, min_length=1, max_length=512)
    interpretation: Literal["odds_ratio", "incidence_rate_ratio", "geometric_mean_ratio"]
    log_scale_estimate: float
    standard_error: float = Field(ge=0.0)
    transformed_estimate: float = Field(ge=0.0)
    ci_lower: float = Field(ge=0.0)
    ci_upper: float = Field(ge=0.0)
    two_sided_p_value: float = Field(ge=0.0, le=1.0)


class MarginalProbabilityContrast(ContractModel):
    comparator_probability: float = Field(ge=0.0, le=1.0)
    intervention_probability: float = Field(ge=0.0, le=1.0)
    absolute_probability_difference: float = Field(ge=-1.0, le=1.0)
    ci_lower: float = Field(ge=-1.0, le=1.0)
    ci_upper: float = Field(ge=-1.0, le=1.0)
    simulation_draws: Literal[5000] = 5000
    rng_seed: Literal[2026071901] = RNG_SEED


class OutcomeModelResult(ContractModel):
    outcome: Literal["verified_detection", "false_positive_count", "log_latency"]
    status: Literal["MIXED_MODEL", "GEE_FALLBACK", "FAILED"]
    selected_estimator: str = Field(strict=True, min_length=1, max_length=128)
    observation_count: int = Field(strict=True, ge=1)
    family_cluster_count: int = Field(strict=True, ge=1)
    scenario_count: int = Field(strict=True, ge=1)
    attempts: tuple[FitAttempt, ...] = Field(min_length=1, max_length=8)
    condition_effect: CoefficientEstimate | None
    marginal_probability: MarginalProbabilityContrast | None = None


class MixedEffectsAnalysisReport(ContractModel):
    schema_version: Literal["mixed-effects-analysis-report-1.0.0"]
    analysis_version: Literal["mixed-effects-analysis-1.0.0"] = ANALYSIS_VERSION
    status: Literal["PASS", "PARTIAL", "FAIL"]
    role: Literal["explanatory_sensitivity_analysis"]
    comparator: str = Field(strict=True, pattern=CONDITION_PATTERN)
    intervention: str = Field(strict=True, pattern=CONDITION_PATTERN)
    statsmodels_version: Literal["0.14.6"]
    numpy_version: str = Field(strict=True, min_length=1, max_length=64)
    scipy_version: str = Field(strict=True, min_length=1, max_length=64)
    dependency_lock_sha256: Sha256
    source_sha256: Sha256
    input_files: tuple[InputFileHash, ...] = Field(min_length=3, max_length=3)
    outcomes: tuple[OutcomeModelResult, ...] = Field(min_length=3, max_length=3)
    primary_bootstrap_recomputed: Literal[False] = False
    output_payload_sha256: Sha256

    @model_validator(mode="after")
    def validate_payload_hash(self) -> MixedEffectsAnalysisReport:
        payload = self.model_dump(mode="json", exclude={"output_payload_sha256"})
        observed = hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()
        if observed != str(self.output_payload_sha256):
            raise ValueError("output payload SHA-256 mismatch")
        return self


def _diagnostic(value: object) -> tuple[str, str]:
    text = " ".join(str(value).split())[:1024] or "no diagnostic supplied"
    return text, hashlib.sha256(text.encode("utf-8")).hexdigest()


def _attempt(
    *,
    ordinal: int,
    specification: str,
    estimator: str,
    optimizer: str | None,
    status: Literal["SUCCESS", "FAILED", "UNAVAILABLE"],
    converged: bool | None,
    warning_count: int,
    diagnostic: object,
) -> FitAttempt:
    text, digest = _diagnostic(diagnostic)
    return FitAttempt(
        ordinal=ordinal,
        specification=specification,
        estimator=estimator,
        optimizer=optimizer,
        status=status,
        converged=converged,
        warning_count=warning_count,
        diagnostic=text,
        diagnostic_sha256=digest,
    )


def _load_csv(path: Path, required: set[str], noun: str) -> pd.DataFrame:
    if path.is_symlink() or not path.is_file():
        raise MixedEffectsAnalysisError(f"{noun} input is missing or a symlink")
    try:
        frame = pd.read_csv(path)
    except Exception as exc:  # pandas exposes several parser exception types
        raise MixedEffectsAnalysisError(f"cannot parse {noun} CSV: {exc}") from exc
    missing = required - set(frame.columns)
    if missing:
        raise MixedEffectsAnalysisError(f"{noun} CSV lacks columns: {sorted(missing)}")
    if frame.empty:
        raise MixedEffectsAnalysisError(f"{noun} CSV is empty")
    if frame[list(required)].isnull().any().any():
        raise MixedEffectsAnalysisError(f"{noun} CSV contains null required values")
    return frame


def _validate_categories(
    frame: pd.DataFrame,
    *,
    comparator: str,
    intervention: str,
    noun: str,
) -> pd.DataFrame:
    observed = set(frame["condition"].astype(str))
    expected = {comparator, intervention}
    if observed != expected:
        raise MixedEffectsAnalysisError(
            f"{noun} conditions differ from primary pair: {sorted(observed)}"
        )
    result = frame.copy()
    result["condition"] = pd.Categorical(
        result["condition"], categories=[comparator, intervention], ordered=True
    )
    result["repetition"] = pd.Categorical(
        result["repetition"], categories=[1, 2, 3, 4, 5], ordered=True
    )
    return result


def _condition_term(names: Sequence[str], intervention: str) -> str:
    exact = f"C(condition)[T.{intervention}]"
    if exact in names:
        return exact
    matches = [name for name in names if name.startswith("C(condition)") and ":" not in name]
    if len(matches) != 1:
        raise MixedEffectsAnalysisError("cannot identify unique primary condition coefficient")
    return matches[0]


def _coefficient(
    *,
    names: Sequence[str],
    values: Sequence[float],
    standard_errors: Sequence[float],
    intervention: str,
    interpretation: Literal["odds_ratio", "incidence_rate_ratio", "geometric_mean_ratio"],
) -> CoefficientEstimate:
    term = _condition_term(names, intervention)
    index = list(names).index(term)
    estimate = float(values[index])
    standard_error = float(standard_errors[index])
    if not math.isfinite(estimate) or not math.isfinite(standard_error) or standard_error < 0:
        raise MixedEffectsAnalysisError("condition estimate is non-finite")
    lower_log = estimate - 1.959963984540054 * standard_error
    upper_log = estimate + 1.959963984540054 * standard_error
    p_value = (
        0.0
        if standard_error == 0 and estimate != 0
        else (
            1.0
            if standard_error == 0
            else float(2 * scipy.stats.norm.sf(abs(estimate / standard_error)))
        )
    )
    return CoefficientEstimate(
        term=term,
        interpretation=interpretation,
        log_scale_estimate=estimate,
        standard_error=standard_error,
        transformed_estimate=float(math.exp(estimate)),
        ci_lower=float(math.exp(lower_log)),
        ci_upper=float(math.exp(upper_log)),
        two_sided_p_value=p_value,
    )


def _marginal_probability(
    *,
    frame: pd.DataFrame,
    design_info: Any,
    fixed_mean: np.ndarray,
    fixed_covariance: np.ndarray,
    comparator: str,
    intervention: str,
) -> MarginalProbabilityContrast:
    # Patsy is an explicit statsmodels dependency and preserves the frozen formula coding.
    from patsy import build_design_matrices  # type: ignore[import-untyped]

    designs: list[np.ndarray] = []
    probabilities: list[float] = []
    for condition in (comparator, intervention):
        counterfactual = frame.copy()
        counterfactual["condition"] = pd.Categorical(
            [condition] * len(counterfactual),
            categories=[comparator, intervention],
            ordered=True,
        )
        matrix = np.asarray(
            build_design_matrices([design_info], counterfactual, return_type="dataframe")[0],
            dtype=float,
        )
        designs.append(matrix)
        probabilities.append(float(np.mean(scipy.special.expit(matrix @ fixed_mean))))
    covariance = np.asarray(fixed_covariance, dtype=float)
    covariance = (covariance + covariance.T) / 2
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    covariance_psd = (eigenvectors * np.clip(eigenvalues, 0.0, None)) @ eigenvectors.T
    rng = np.random.default_rng(RNG_SEED)
    draws = rng.multivariate_normal(fixed_mean, covariance_psd, size=5000)
    comparator_draw = np.mean(scipy.special.expit(designs[0] @ draws.T), axis=0)
    intervention_draw = np.mean(scipy.special.expit(designs[1] @ draws.T), axis=0)
    differences = intervention_draw - comparator_draw
    return MarginalProbabilityContrast(
        comparator_probability=probabilities[0],
        intervention_probability=probabilities[1],
        absolute_probability_difference=probabilities[1] - probabilities[0],
        ci_lower=float(np.quantile(differences, 0.025)),
        ci_upper=float(np.quantile(differences, 0.975)),
    )


def _captured_fit(function: Callable[[], Any]) -> tuple[Any, tuple[str, ...]]:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = function()
    messages = tuple(" ".join(str(item.message).split())[:256] for item in caught)
    return result, messages


def _positive_model(
    frame: pd.DataFrame, *, comparator: str, intervention: str
) -> OutcomeModelResult:
    # statsmodels draws the MAP optimizer start from NumPy's legacy global RNG.
    # Fix that otherwise-hidden source of refit variability for the public replay.
    np.random.seed(RNG_SEED)
    formula = (
        "verified_detected ~ C(condition) + C(finding_type) + recent_kev + "
        "C(repetition) + C(condition):recent_kev"
    )
    random = {"scenario_family": "0 + C(scenario_family)"}
    attempts: list[FitAttempt] = []
    selected: Any | None = None
    selected_model: Any | None = None
    status: Literal["MIXED_MODEL", "GEE_FALLBACK", "FAILED"] = "FAILED"
    estimator = "none"
    for ordinal, optimizer in ((1, "BFGS"), (2, "L-BFGS-B")):
        try:
            model = BinomialBayesMixedGLM.from_formula(
                formula, random, frame, vcp_p=0.5, fe_p=10.0
            )
            result, caught = _captured_fit(
                lambda model=model, optimizer=optimizer: model.fit_map(  # type: ignore[misc]
                    method=optimizer,
                    minim_opts={"maxiter": 1000},
                    scale_fe=False,
                )
            )
            converged = bool(result.optim_retvals.get("success", False))
            attempts.append(
                _attempt(
                    ordinal=ordinal,
                    specification=formula + " + (1|scenario_family)",
                    estimator="BinomialBayesMixedGLM Laplace MAP",
                    optimizer=optimizer,
                    status="SUCCESS" if converged else "FAILED",
                    converged=converged,
                    warning_count=len(caught),
                    diagnostic=(
                        f"optimizer_message={result.optim_retvals.get('message')}; "
                        f"warnings={' | '.join(caught) or 'none'}"
                    ),
                )
            )
            if converged:
                selected = result
                selected_model = model
                status = "MIXED_MODEL"
                estimator = f"BinomialBayesMixedGLM Laplace MAP ({optimizer})"
                break
        except Exception as exc:
            attempts.append(
                _attempt(
                    ordinal=ordinal,
                    specification=formula + " + (1|scenario_family)",
                    estimator="BinomialBayesMixedGLM Laplace MAP",
                    optimizer=optimizer,
                    status="FAILED",
                    converged=False,
                    warning_count=0,
                    diagnostic=f"{type(exc).__name__}: {exc}",
                )
            )
    if selected is None:
        ordinal = len(attempts) + 1
        try:
            model = smf.gee(
                formula,
                groups="scenario_family",
                data=frame,
                family=sm.families.Binomial(),
                cov_struct=sm.cov_struct.Exchangeable(),
            )
            result, caught = _captured_fit(
                lambda: model.fit(maxiter=200, cov_type="robust")
            )
            converged = bool(result.converged)
            attempts.append(
                _attempt(
                    ordinal=ordinal,
                    specification=formula + "; family-cluster exchangeable correlation",
                    estimator="Binomial GEE robust",
                    optimizer="GEE iterative",
                    status="SUCCESS" if converged else "FAILED",
                    converged=converged,
                    warning_count=len(caught),
                    diagnostic=f"warnings={' | '.join(caught) or 'none'}",
                )
            )
            if converged:
                selected = result
                selected_model = model
                status = "GEE_FALLBACK"
                estimator = "Binomial GEE robust exchangeable"
        except Exception as exc:
            attempts.append(
                _attempt(
                    ordinal=ordinal,
                    specification=formula + "; family-cluster exchangeable correlation",
                    estimator="Binomial GEE robust",
                    optimizer="GEE iterative",
                    status="FAILED",
                    converged=False,
                    warning_count=0,
                    diagnostic=f"{type(exc).__name__}: {exc}",
                )
            )
    coefficient = None
    marginal = None
    if selected is not None and selected_model is not None:
        if status == "MIXED_MODEL":
            names = tuple(selected_model.exog_names)
            values = np.asarray(selected.fe_mean, dtype=float)
            errors = np.asarray(selected.fe_sd, dtype=float)
            covariance = np.asarray(selected.cov_params(), dtype=float)[: len(names), : len(names)]
        else:
            names = tuple(selected.model.exog_names)
            values = np.asarray(selected.params, dtype=float)
            with np.errstate(invalid="ignore"):
                errors = np.asarray(selected.bse, dtype=float)
            covariance = np.asarray(selected.cov_params(), dtype=float)
        coefficient = _coefficient(
            names=names,
            values=tuple(float(item) for item in values),
            standard_errors=tuple(float(item) for item in errors),
            intervention=intervention,
            interpretation="odds_ratio",
        )
        marginal = _marginal_probability(
            frame=frame,
            design_info=selected_model.data.design_info,
            fixed_mean=values,
            fixed_covariance=covariance,
            comparator=comparator,
            intervention=intervention,
        )
    return OutcomeModelResult(
        outcome="verified_detection",
        status=status,
        selected_estimator=estimator,
        observation_count=len(frame),
        family_cluster_count=frame["scenario_family"].nunique(),
        scenario_count=frame["scenario_id"].nunique(),
        attempts=tuple(attempts),
        condition_effect=coefficient,
        marginal_probability=marginal,
    )


def _gee_count_model(frame: pd.DataFrame, *, intervention: str) -> OutcomeModelResult:
    formula = "fp_count ~ C(condition) + C(scenario_stratum) + C(repetition)"
    unavailable = _attempt(
        ordinal=1,
        specification=(
            formula
            + " + offset(log_evaluated_assets_offset) + (1|scenario_family) + (1|scenario_id)"
        ),
        estimator="negative-binomial GLMM",
        optimizer=None,
        status="UNAVAILABLE",
        converged=None,
        warning_count=0,
        diagnostic=(
            "statsmodels 0.14.6 has binomial/Poisson Bayesian GLMM and linear MixedLM but no "
            "negative-binomial GLMM; apply the prespecified family-cluster GEE fallback"
        ),
    )
    attempts = [unavailable]
    selected: Any | None = None
    try:
        model = smf.gee(
            formula,
            groups="scenario_family",
            data=frame,
            offset=frame["log_evaluated_assets_offset"],
            family=sm.families.NegativeBinomial(alpha=1.0),
            cov_struct=sm.cov_struct.Exchangeable(),
        )
        result, caught = _captured_fit(lambda: model.fit(maxiter=200, cov_type="robust"))
        converged = bool(result.converged)
        attempts.append(
            _attempt(
                ordinal=2,
                specification=formula + "; NB2 alpha=1; offset; family-cluster exchangeable",
                estimator="negative-binomial GEE robust",
                optimizer="GEE iterative",
                status="SUCCESS" if converged else "FAILED",
                converged=converged,
                warning_count=len(caught),
                diagnostic=f"warnings={' | '.join(caught) or 'none'}",
            )
        )
        if converged:
            selected = result
    except Exception as exc:
        attempts.append(
            _attempt(
                ordinal=2,
                specification=formula + "; NB2 alpha=1; offset; family-cluster exchangeable",
                estimator="negative-binomial GEE robust",
                optimizer="GEE iterative",
                status="FAILED",
                converged=False,
                warning_count=0,
                diagnostic=f"{type(exc).__name__}: {exc}",
            )
        )
    coefficient = None
    if selected is not None:
        with np.errstate(invalid="ignore"):
            standard_errors = np.asarray(selected.bse, dtype=float)
        coefficient = _coefficient(
            names=tuple(selected.model.exog_names),
            values=tuple(float(item) for item in np.asarray(selected.params, dtype=float)),
            standard_errors=tuple(
                float(item) for item in standard_errors
            ),
            intervention=intervention,
            interpretation="incidence_rate_ratio",
        )
    return OutcomeModelResult(
        outcome="false_positive_count",
        status="GEE_FALLBACK" if selected is not None else "FAILED",
        selected_estimator=(
            "negative-binomial GEE robust exchangeable" if selected is not None else "none"
        ),
        observation_count=len(frame),
        family_cluster_count=frame["scenario_family"].nunique(),
        scenario_count=frame["scenario_id"].nunique(),
        attempts=tuple(attempts),
        condition_effect=coefficient,
    )


def _latency_model(frame: pd.DataFrame, *, intervention: str) -> OutcomeModelResult:
    formula = "log_latency ~ C(condition) + C(scenario_stratum)"
    attempts: list[FitAttempt] = []
    selected: Any | None = None
    estimator = "none"
    status: Literal["MIXED_MODEL", "GEE_FALLBACK", "FAILED"] = "FAILED"
    specifications = (
        ("lbfgs", {"scenario": "0 + C(scenario_id)"}, "family and scenario random intercepts"),
        ("powell", {"scenario": "0 + C(scenario_id)"}, "family and scenario random intercepts"),
        ("lbfgs", None, "family random intercept; lowest-variance scenario effect removed"),
    )
    for ordinal, (optimizer, variance_components, label) in enumerate(specifications, 1):
        try:
            model = smf.mixedlm(
                formula,
                frame,
                groups=frame["scenario_family"],
                re_formula="1",
                vc_formula=variance_components,
            )
            result, caught = _captured_fit(
                lambda model=model, optimizer=optimizer: model.fit(  # type: ignore[misc]
                    reml=False, method=optimizer, maxiter=1000, disp=False
                )
            )
            converged = bool(result.converged)
            attempts.append(
                _attempt(
                    ordinal=ordinal,
                    specification=f"{formula}; {label}",
                    estimator="Gaussian MixedLM on log latency",
                    optimizer=optimizer,
                    status="SUCCESS" if converged else "FAILED",
                    converged=converged,
                    warning_count=len(caught),
                    diagnostic=f"warnings={' | '.join(caught) or 'none'}",
                )
            )
            if converged:
                selected = result
                status = "MIXED_MODEL"
                estimator = f"Gaussian MixedLM ML ({optimizer}; {label})"
                break
        except Exception as exc:
            attempts.append(
                _attempt(
                    ordinal=ordinal,
                    specification=f"{formula}; {label}",
                    estimator="Gaussian MixedLM on log latency",
                    optimizer=optimizer,
                    status="FAILED",
                    converged=False,
                    warning_count=0,
                    diagnostic=f"{type(exc).__name__}: {exc}",
                )
            )
    if selected is None:
        ordinal = len(attempts) + 1
        try:
            model = smf.gee(
                formula,
                groups="scenario_family",
                data=frame,
                family=sm.families.Gaussian(),
                cov_struct=sm.cov_struct.Exchangeable(),
            )
            result, caught = _captured_fit(
                lambda: model.fit(maxiter=200, cov_type="robust")
            )
            converged = bool(result.converged)
            attempts.append(
                _attempt(
                    ordinal=ordinal,
                    specification=formula + "; family-cluster exchangeable correlation",
                    estimator="Gaussian GEE robust on log latency",
                    optimizer="GEE iterative",
                    status="SUCCESS" if converged else "FAILED",
                    converged=converged,
                    warning_count=len(caught),
                    diagnostic=f"warnings={' | '.join(caught) or 'none'}",
                )
            )
            if converged:
                selected = result
                status = "GEE_FALLBACK"
                estimator = "Gaussian GEE robust exchangeable on log latency"
        except Exception as exc:
            attempts.append(
                _attempt(
                    ordinal=ordinal,
                    specification=formula + "; family-cluster exchangeable correlation",
                    estimator="Gaussian GEE robust on log latency",
                    optimizer="GEE iterative",
                    status="FAILED",
                    converged=False,
                    warning_count=0,
                    diagnostic=f"{type(exc).__name__}: {exc}",
                )
            )
    coefficient = None
    if selected is not None:
        names = tuple(selected.model.exog_names)
        values = np.asarray(selected.fe_params if status == "MIXED_MODEL" else selected.params)
        with np.errstate(invalid="ignore"):
            errors = np.asarray(selected.bse_fe if status == "MIXED_MODEL" else selected.bse)
        coefficient = _coefficient(
            names=names,
            values=tuple(float(item) for item in values),
            standard_errors=tuple(float(item) for item in errors),
            intervention=intervention,
            interpretation="geometric_mean_ratio",
        )
    return OutcomeModelResult(
        outcome="log_latency",
        status=status,
        selected_estimator=estimator,
        observation_count=len(frame),
        family_cluster_count=frame["scenario_family"].nunique(),
        scenario_count=frame["scenario_id"].nunique(),
        attempts=tuple(attempts),
        condition_effect=coefficient,
    )


def analyze_mixed_effects(
    *,
    scoring_output_directory: Path,
    dependency_lock: Path,
    comparator: str,
    intervention: str,
    require_primary_matrix: bool = True,
) -> MixedEffectsAnalysisReport:
    """Validate scorer rows and run the frozen explanatory-model sequence."""

    if comparator == intervention:
        raise MixedEffectsAnalysisError("comparator and intervention must differ")
    if statsmodels.__version__ != EXPECTED_STATSMODELS_VERSION:
        raise MixedEffectsAnalysisError("statsmodels version differs from frozen analysis version")
    root = scoring_output_directory.resolve()
    if not root.is_dir() or root.is_symlink():
        raise MixedEffectsAnalysisError("scoring output directory is missing or a symlink")
    lock = dependency_lock.resolve()
    if lock.is_symlink() or not lock.is_file():
        raise MixedEffectsAnalysisError("dependency lock is missing or a symlink")
    paths = {
        "positive": root / "mixed_effects_positive_rows.csv",
        "fp": root / "mixed_effects_fp_rows.csv",
        "latency": root / "mixed_effects_latency_rows.csv",
    }
    positive = _load_csv(
        paths["positive"],
        {
            "scenario_id",
            "scenario_family",
            "condition",
            "repetition",
            "finding_type",
            "recent_kev",
            "verified_detected",
        },
        "positive-candidate",
    )
    fp = _load_csv(
        paths["fp"],
        {
            "scenario_id",
            "scenario_family",
            "condition",
            "scenario_stratum",
            "repetition",
            "fp_count",
            "evaluated_assets",
            "log_evaluated_assets_offset",
        },
        "false-positive",
    )
    latency = _load_csv(
        paths["latency"],
        {
            "scenario_id",
            "scenario_family",
            "condition",
            "scenario_stratum",
            "repetition",
            "latency_seconds",
            "log_latency",
        },
        "latency",
    )
    for noun, frame in (("positive", positive), ("false-positive", fp), ("latency", latency)):
        frame = _validate_categories(
            frame, comparator=comparator, intervention=intervention, noun=noun
        )
        if noun == "positive":
            positive = frame
        elif noun == "false-positive":
            fp = frame
        else:
            latency = frame
    if not set(positive["verified_detected"]).issubset({0, 1}):
        raise MixedEffectsAnalysisError("verified_detected must be binary")
    if (fp["fp_count"] < 0).any() or (fp["evaluated_assets"] <= 0).any():
        raise MixedEffectsAnalysisError("FP counts/assets violate nonnegative/positive bounds")
    if (latency["latency_seconds"] <= 0).any():
        raise MixedEffectsAnalysisError("latency analysis requires positive latency")
    if not np.allclose(np.log(fp["evaluated_assets"]), fp["log_evaluated_assets_offset"]):
        raise MixedEffectsAnalysisError("FP offset differs from log(evaluated_assets)")
    if not np.allclose(np.log(latency["latency_seconds"]), latency["log_latency"]):
        raise MixedEffectsAnalysisError("log_latency differs from latency_seconds")
    if require_primary_matrix:
        if len(positive) != 250 or len(fp) != 600 or len(latency) > 600:
            raise MixedEffectsAnalysisError(
                "primary matrix requires 250 positive, 600 FP, and at most 600 latency rows"
            )
        if fp["scenario_family"].nunique() != 30 or fp["scenario_id"].nunique() != 60:
            raise MixedEffectsAnalysisError("primary explanatory rows require 30 families/60 cases")

    outcomes = (
        _positive_model(positive, comparator=comparator, intervention=intervention),
        _gee_count_model(fp, intervention=intervention),
        _latency_model(latency, intervention=intervention),
    )
    succeeded = sum(item.status != "FAILED" for item in outcomes)
    report_status: Literal["PASS", "PARTIAL", "FAIL"] = (
        "PASS" if succeeded == 3 else ("PARTIAL" if succeeded else "FAIL")
    )
    source = Path(__file__).resolve()
    inputs = tuple(
        InputFileHash(
            relative_path=path.relative_to(root).as_posix(),
            sha256=_file_sha256(path),
            size_bytes=path.stat().st_size,
        )
        for path in paths.values()
    )
    base: dict[str, object] = {
        "schema_version": "mixed-effects-analysis-report-1.0.0",
        "analysis_version": ANALYSIS_VERSION,
        "status": report_status,
        "role": "explanatory_sensitivity_analysis",
        "comparator": comparator,
        "intervention": intervention,
        "statsmodels_version": statsmodels.__version__,
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "dependency_lock_sha256": _file_sha256(lock),
        "source_sha256": _file_sha256(source),
        "input_files": [item.model_dump(mode="json") for item in inputs],
        "outcomes": [item.model_dump(mode="json") for item in outcomes],
        "primary_bootstrap_recomputed": False,
    }
    base["output_payload_sha256"] = hashlib.sha256(_canonical_json_bytes(base)).hexdigest()
    return MixedEffectsAnalysisReport.model_validate_json(_canonical_json_bytes(base))


def write_report_once(path: Path, report: MixedEffectsAnalysisReport) -> Path:
    """Atomically create one immutable report without overwriting an existing result."""

    resolved = path.resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    temporary = resolved.with_name(resolved.name + ".tmp")
    if resolved.exists() or temporary.exists():
        raise MixedEffectsAnalysisError("mixed-effects report path already exists")
    payload = _canonical_json_bytes(report.model_dump(mode="json"), newline=True)
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, resolved)
        temporary.unlink()
    except Exception:
        if temporary.exists() and not resolved.exists():
            temporary.unlink()
        raise
    return resolved


__all__ = [
    "ANALYSIS_VERSION",
    "MixedEffectsAnalysisError",
    "MixedEffectsAnalysisReport",
    "analyze_mixed_effects",
    "write_report_once",
]
