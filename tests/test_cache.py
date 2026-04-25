from semantic_cache import _cosine_similarity


def test_identical_vectors_return_one():
    assert _cosine_similarity([1.0, 0.0, 0.0], [1.0, 0.0, 0.0]) == 1.0


def test_orthogonal_vectors_return_zero():
    assert _cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_zero_vector_returns_zero():
    assert _cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_similar_vectors_above_threshold():
    a = [0.9, 0.1]
    b = [0.95, 0.05]
    score = _cosine_similarity(a, b)
    assert score > 0.8


def test_dissimilar_vectors_below_threshold():
    a = [1.0, 0.0]
    b = [0.1, 0.99]
    score = _cosine_similarity(a, b)
    assert score < 0.8
