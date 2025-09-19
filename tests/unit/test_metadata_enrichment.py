from metadata.enrichment import enrich_metadata


def test_enrichment_adds_topics_and_concepts():
    metadata = {
        "title": "A stochastic analysis of optimization algorithms",
        "abstract": "We study gradient methods with Markov sampling.",
        "journal": "Annals of Mathematics",
        "arxiv_id": "math.PR/1234567",
    }
    result = enrich_metadata(metadata)

    assert "probability" in result.topics
    assert "Mathematics" == result.subject_area
    assert result.journal_quality == {"tier": "A+"}
    assert "markov chain" in result.math_concepts
    assert metadata["topics"] == result.topics
