"""Eight-dimensional exact KNN research reference; no source/repository input."""
import math
import re
import numpy as np
from sklearn.preprocessing import StandardScaler

NAMES = ["log_length", "shannon_entropy", "digit_ratio", "uppercase_ratio",
         "symbol_ratio", "keyword_proximity", "sensitive_assignment", "placeholder_similarity"]


class ResearchError(ValueError):
    pass


def require(condition, code="research_contract_mismatch"):
    if not condition:
        raise ResearchError(code)


def matrix(values):
    try:
        raw = np.asarray(values)
    except (ValueError, TypeError, OverflowError):
        raise ResearchError("invalid_eight_column_matrix") from None
    require(raw.dtype.kind in "iuf" and raw.ndim == 2 and raw.shape[1] == 8 and len(raw) > 0,
            "invalid_eight_column_matrix")
    require(not any(isinstance(v, (bool, np.bool_)) for row in values for v in row), "boolean_coordinate")
    result = raw.astype(np.float64)
    require(bool(np.isfinite(result).all()), "non_finite_matrix")
    return result


def eight(values):
    result = matrix([values])
    return result[0]


def validate_ids(ids, count):
    require(len(ids) == count and len(set(ids)) == count, "duplicate_or_missing_reference_id")
    require(all(isinstance(i, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", i) for i in ids),
            "invalid_reference_id")


def labels(values, count):
    result = np.asarray(values)
    require(result.shape == (count,) and result.dtype.kind in "iub"
            and bool(np.isin(result, [0, 1]).all()), "invalid_reference_labels")
    return result.astype(np.int64)


class ExactKNN:
    def __init__(self, values, outcomes, ids, k=3, weights="inverse_distance", standardised=True):
        x = matrix(values)
        require(len(x) <= 10_000, "reference_limit")
        validate_ids(ids, len(x))
        self.ids = np.asarray(ids)
        self.y = labels(outcomes, len(x))
        self.k, self.weights = k, weights
        self.validate_config(k, weights)
        self.lower, self.upper = x.min(axis=0), x.max(axis=0)
        if standardised:
            scaler = StandardScaler().fit(x)
            self.mean, self.scale = scaler.mean_.copy(), scaler.scale_.copy()
        else:
            self.mean, self.scale = np.zeros(8), np.ones(8)
        require(bool((self.scale > 0).all()) and bool(np.isfinite(self.scale).all()))
        self.z = (x - self.mean) / self.scale
        require(bool(np.isfinite(self.z).all()))

    def validate_config(self, k, weights):
        require(type(k) is int and 1 <= k <= len(self.y), "invalid_neighbour_count")
        require(weights in ("inverse_distance", "uniform"), "invalid_weighting")

    def neighbours(self, queries, maximum_k=None):
        maximum_k = self.k if maximum_k is None else maximum_k
        self.validate_config(maximum_k, self.weights)
        for query in matrix(queries):
            z = (query - self.mean) / self.scale
            require(bool(np.isfinite(z).all()), "non_finite_query")
            # Fixed coordinate reduction order, for the later native implementation.
            squared = np.zeros(len(self.z), dtype=np.float64)
            with np.errstate(over="ignore", invalid="ignore"):
                for coordinate in range(8):
                    delta = self.z[:, coordinate] - z[coordinate]
                    squared += delta * delta
            require(bool(np.isfinite(squared).all()), "distance_overflow")
            distances = np.sqrt(squared)
            order = np.lexsort((self.ids, distances))
            zero = np.flatnonzero(squared == 0.0)
            selected = order[:maximum_k]
            yield {
                "indices": selected, "distances": distances[selected],
                "nearest": float(distances[order[0]]),
                "zero_count": int(len(zero)),
                "zero_vote": float(self.y[zero].mean()) if len(zero) else None,
                "conflict": bool(len(zero) and len(np.unique(self.y[zero])) > 1),
                "outside": bool(((query < self.lower) | (query > self.upper)).any()),
            }

    def vote(self, info, k=None, weights=None):
        k = self.k if k is None else k
        weights = self.weights if weights is None else weights
        self.validate_config(k, weights)
        if info["zero_count"]:
            return info["zero_vote"]
        selected = info["indices"][:k]
        distances = info["distances"][:k]
        require(len(selected) == k and bool((distances > 0).all()))
        coefficients = [1.0 if weights == "uniform" else 1.0 / float(d) for d in distances]
        denominator = sum(coefficients)
        require(math.isfinite(denominator) and denominator > 0, "invalid_vote")
        score = sum(w for w, outcome in zip(coefficients, self.y[selected]) if outcome == 1) / denominator
        require(math.isfinite(score) and 0 <= score <= 1, "invalid_vote")
        return float(score)

    def predict(self, values, policy=None):
        result = []
        for info in self.neighbours(values):
            score = self.vote(info)
            reason = (review_reason(score, info, policy) if policy is not None else
                      "exact_match_conflict" if info["conflict"] else
                      "outside_training_support" if info["outside"] else None)
            result.append({"score": score, "nearest": info["nearest"], "conflict": info["conflict"],
                           "outside": info["outside"], "zero_count": info["zero_count"],
                           "prediction": None if reason else int(score >= 0.5), "review_reason": reason})
        return result

    def bundle(self, metadata, policy):
        return {
            "schema": "veilguard.knn-model.v1", "feature_schema": "veilguard.features.v1",
            "feature_names": NAMES, "label_encoding": {"0": "benign_fixture", "1": "sensitive_candidate"}, "status": "experimental_research_only",
            "model_id": metadata["model_id"], "corpus_source_sha256": metadata["corpus_source_sha256"],
            "protocol_sha256": metadata["protocol_sha256"], "training_partition": "train",
            "k": self.k, "weights": self.weights, "mean": self.mean.tolist(), "scale": self.scale.tolist(),
            "raw_min": self.lower.tolist(), "raw_max": self.upper.tolist(), "policy": policy,
            "references": [{"id": str(identifier), "label": int(outcome), "vector": vector.tolist()}
                           for identifier, outcome, vector in zip(self.ids, self.y, self.z)],
        }

    @classmethod
    def from_bundle(cls, bundle):
        fields = {"schema", "feature_schema", "feature_names", "status", "model_id", "corpus_source_sha256",
                  "protocol_sha256", "label_encoding", "training_partition", "k", "weights", "mean", "scale", "raw_min",
                  "raw_max", "policy", "references"}
        require(set(bundle) == fields, "model_fields_mismatch")
        require(bundle["schema"] == "veilguard.knn-model.v1"
                and bundle["feature_schema"] == "veilguard.features.v1"
                and bundle["feature_names"] == NAMES and bundle["training_partition"] == "train"
                and bundle["status"] == "experimental_research_only", "model_version_mismatch")
        require(bundle["label_encoding"] == {"0": "benign_fixture", "1": "sensitive_candidate"})
        require(re.fullmatch(r"[A-Za-z0-9_-]{1,128}", bundle["model_id"]) is not None)
        require(all(re.fullmatch(r"[0-9a-f]{64}", bundle[k]) is not None
                    for k in ("corpus_source_sha256", "protocol_sha256")))
        references = bundle["references"]
        require(isinstance(references, list) and 1 <= len(references) <= 10_000, "reference_limit")
        require(all(set(row) == {"id", "label", "vector"} for row in references))
        require(all(type(row["label"]) is int for row in references), "invalid_reference_labels")
        instance = cls.__new__(cls)
        instance.z = matrix([r["vector"] for r in references])
        instance.y = labels([r["label"] for r in references], len(references))
        ids = [r["id"] for r in references]
        validate_ids(ids, len(references))
        instance.ids = np.asarray(ids)
        instance.mean, instance.scale = eight(bundle["mean"]), eight(bundle["scale"])
        instance.lower, instance.upper = eight(bundle["raw_min"]), eight(bundle["raw_max"])
        require(bool((instance.scale > 0).all()) and bool((instance.lower <= instance.upper).all()))
        instance.k, instance.weights = bundle["k"], bundle["weights"]
        instance.validate_config(instance.k, instance.weights)
        validate_policy(bundle["policy"])
        return instance


def validate_policy(policy):
    require(set(policy) == {"review_all", "margin", "distance_limit", "selection_status"})
    require(type(policy["review_all"]) is bool)
    require(type(policy["margin"]) in (float, int) and math.isfinite(policy["margin"]) and 0 <= policy["margin"] <= 1)
    require(type(policy["distance_limit"]) in (float, int) and math.isfinite(policy["distance_limit"])
            and policy["distance_limit"] >= 0)
    require(policy["selection_status"] in ("validation_selected", "coverage_or_error_target_unmet", "baseline_fixed"))


def review_reason(score, info, policy):
    validate_policy(policy)
    if policy["review_all"]:
        return "validation_policy_unmet"
    if info["conflict"]:
        return "exact_match_conflict"
    if info["outside"]:
        return "outside_training_support"
    if info["nearest"] > policy["distance_limit"]:
        return "nearest_distance_exceeded"
    if abs(2 * score - 1) < policy["margin"]:
        return "low_vote_margin"
    return None
