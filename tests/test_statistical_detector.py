"""Tests for statistical detector."""
import pytest
from pyspark.sql import SparkSession
from src.detectors.statistical_detector import StatisticalDetector
from pyspark.sql.types import StructType, StructField, StringType, IntegerType


@pytest.fixture
def spark_session():
    """Create Spark session for testing."""
    spark = SparkSession.builder \
        .appName("test") \
        .master("local[2]") \
        .getOrCreate()
    yield spark
    spark.stop()


def test_statistical_detector_initialization(spark_session):
    """Test detector initialization."""
    detector = StatisticalDetector(
        spark_session,
        z_score_threshold=3.5,
        ratio_threshold=10.0
    )
    assert detector.z_score_threshold == 3.5
    assert detector.ratio_threshold == 10.0


def test_calculate_robust_z_score(spark_session):
    """Test robust Z-score calculation."""
    detector = StatisticalDetector(spark_session)
    
    z = detector.calculate_robust_z_score(100.0, 10.0, 2.0)
    assert z > 0  # Should be positive for value above median
    
    z = detector.calculate_robust_z_score(5.0, 10.0, 2.0)
    assert z < 0  # Should be negative for value below median


def test_calculate_confidence(spark_session):
    """Test confidence calculation."""
    detector = StatisticalDetector(spark_session)
    
    # High z-score and ratio should give high confidence
    conf = detector.calculate_confidence(5.0, 15.0)
    assert 0 <= conf <= 1
    assert conf > 0.5  # Should be high confidence
    
    # Low z-score and ratio should give low confidence
    conf = detector.calculate_confidence(0.5, 1.5)
    assert 0 <= conf <= 1
    assert conf < 0.5  # Should be low confidence

