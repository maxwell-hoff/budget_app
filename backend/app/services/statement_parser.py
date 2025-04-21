import pandas as pd
from datetime import datetime
from typing import Dict, List

class StatementParser:
    """Service for parsing bank statements and categorizing transactions."""
    
    def __init__(self):
        """Initialize the statement parser."""
        self.transaction_categories = {
            'income': ['PAYROLL', 'DIRECT DEP', 'ACH_CREDIT'],
            'housing': ['RENT', 'MORTGAGE', 'REDWOOD TREE'],
            'utilities': ['ELECTRIC', 'GAS', 'WATER', 'INTERNET'],
            'transportation': ['UBER', 'LYFT', 'CTA', 'VENTRA'],
            'food': ['RESTAURANT', 'GROCERY', 'CAFE', 'MARKET'],
            'entertainment': ['MOVIE', 'CONCERT', 'EVENT'],
            'health': ['DOCTOR', 'HOSPITAL', 'PHARMACY', 'INSURANCE'],
            'debt': ['LOAN', 'CREDIT CARD', 'STUDENT LOAN'],
            'savings': ['SAVINGS', 'INVESTMENT', 'RETIREMENT'],
            'other': []  # Default category
        }
    
    def parse_chase_csv(self, file_path: str) -> pd.DataFrame:
        """
        Parse a Chase bank statement CSV file.
        
        Args:
            file_path (str): Path to the CSV file
            
        Returns:
            pd.DataFrame: DataFrame containing the parsed transactions
        """
        # Read the CSV file
        df = pd.read_csv(file_path)
        
        # Convert date strings to datetime objects
        df['Posting Date'] = pd.to_datetime(df['Posting Date'])
        
        # Convert amount strings to floats
        df['Amount'] = df['Amount'].astype(float)
        
        # Add category column
        df['Category'] = df['Description'].apply(self._categorize_transaction)
        
        return df
    
    def _categorize_transaction(self, description: str) -> str:
        """
        Categorize a transaction based on its description.
        
        Args:
            description (str): Transaction description
            
        Returns:
            str: Transaction category
        """
        description = description.upper()
        
        for category, keywords in self.transaction_categories.items():
            if any(keyword in description for keyword in keywords):
                return category
        
        return 'other'
    
    def calculate_balance_sheet(self, transactions: pd.DataFrame) -> Dict:
        """
        Calculate a simple balance sheet from transactions.
        
        Args:
            transactions (pd.DataFrame): DataFrame of transactions
            
        Returns:
            Dict: Dictionary containing balance sheet information
        """
        # Calculate total income
        income = transactions[transactions['Amount'] > 0]['Amount'].sum()
        
        # Calculate total expenses by category
        expenses = transactions[transactions['Amount'] < 0].groupby('Category')['Amount'].sum().to_dict()
        
        # Calculate net worth
        net_worth = income + sum(expenses.values())
        
        return {
            'total_income': income,
            'expenses_by_category': expenses,
            'net_worth': net_worth
        } 