import pandas as pd
from datetime import datetime

class StatementParser:
    """Service for parsing bank statements and extracting the latest balance."""
    
    def parse_chase_csv(self, file_path: str) -> float:
        """
        Parse a Chase bank statement CSV file and return the latest balance.
        
        Args:
            file_path (str): Path to the CSV file
            
        Returns:
            float: The latest balance from the statement
        """
        # Read the CSV file
        df = pd.read_csv(file_path)
        
        # Convert date strings to datetime objects
        df['Posting Date'] = pd.to_datetime(df['Posting Date'])
        
        # Sort by date in descending order
        df = df.sort_values('Posting Date', ascending=False)
        
        # Get the latest balance
        latest_balance = float(df.iloc[0]['Balance'])
        
        return latest_balance 