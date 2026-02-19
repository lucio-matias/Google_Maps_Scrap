
import os
import pandas as pd
import pytest
from app import save_to_csv

def test_save_to_csv(tmp_path):
    # Arrange
    data = [
        {
            "Name": "Test Company", 
            "Full Address": "123 Street", 
            "EMAIL": "test@example.com", 
            "URL": "http://example.com",
            "lat": -22.12345,
            "lng": -42.98765
        },
        {
            "Name": "Another One", 
            "Full Address": "456 Avenue", 
            "EMAIL": "info@another.com", 
            "URL": "http://another.com",
            "lat": None,
            "lng": None
        }
    ]
    filename = tmp_path / "output.csv"

    # Act
    save_to_csv(data, str(filename))

    # Assert
    assert os.path.exists(filename)
    df = pd.read_csv(filename)
    assert len(df) == 2
    
    # Check first row
    assert df.iloc[0]["Name"] == "Test Company"
    assert df.iloc[0]["lat"] == -22.12345
    assert df.iloc[0]["lng"] == -42.98765
    
    # Check second row (handling NaN for None in pandas)
    assert df.iloc[1]["EMAIL"] == "info@another.com"
    assert pd.isna(df.iloc[1]["lat"])

def test_save_to_csv_empty(capsys):
    # Arrange
    data = []

    # Act
    save_to_csv(data)

    # Assert
    captured = capsys.readouterr()
    assert "Nenhum dado para salvar." in captured.out
