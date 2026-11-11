import numpy as np

from vigil.storage.embeddings import EmbeddingStore
from vigil.storage.schema import create_schema, make_engine


def test_embedding_round_trip_preserves_values(tmp_path):
    db = tmp_path / "vigil.db"
    engine = make_engine(db)
    create_schema(engine)
    store = EmbeddingStore(engine)

    vector = np.linspace(-1.0, 1.0, 128, dtype=np.float32)
    store.add(person_id=1, person_image_id=None, model_id="dlib_resnet", vector=vector)

    gallery = store.gallery("dlib_resnet")
    assert 1 in gallery
    assert gallery[1].shape == (128,)
    assert np.allclose(gallery[1], vector, atol=1e-6)


def test_gallery_groups_images_by_person(tmp_path):
    store = EmbeddingStore(create_schema(make_engine(tmp_path / "vigil.db")))
    store.add(1, None, "dlib_resnet", np.zeros(128, dtype=np.float32))
    store.add(1, None, "dlib_resnet", np.ones(128, dtype=np.float32))
    store.add(2, None, "dlib_resnet", np.full(128, 0.5, dtype=np.float32))

    gallery = store.gallery("dlib_resnet")
    assert gallery[1].shape == (2, 128)
    assert gallery[2].shape == (1, 128)


def test_remove_person_clears_embeddings(tmp_path):
    store = EmbeddingStore(create_schema(make_engine(tmp_path / "vigil.db")))
    store.add(1, None, "dlib_resnet", np.zeros(128, dtype=np.float32))
    store.remove_person(1)
    assert store.gallery("dlib_resnet") == {}


def test_gallery_ignores_other_models(tmp_path):
    store = EmbeddingStore(create_schema(make_engine(tmp_path / "vigil.db")))
    store.add(1, None, "dlib_resnet", np.zeros(128, dtype=np.float32))
    assert store.gallery("arcface") == {}
