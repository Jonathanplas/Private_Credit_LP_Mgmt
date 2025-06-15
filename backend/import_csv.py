import pandas as pd
from sqlalchemy.orm import Session
from backend.db import engine
from backend.models import tbLPLookup, tbLPFund, tbPCAP, tbLedger
from datetime import datetime


# Define file paths - using relative paths for portability
import os

# Get the absolute path of the project root directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

csv_files = {
    "tbLPLookup": os.path.join(project_root, "data", "tbLPLookup.csv"),
    "tbLPFund": os.path.join(project_root, "data", "tbLPFund.csv"),
    "tbPCAP": os.path.join(project_root, "data", "tbPCAP.csv"),
    "tbLedger": os.path.join(project_root, "data", "tbLedger.csv"),
}

# Define column mappings
column_mappings = {
    "tbLPLookup": {
        "LP Short Name": "short_name",
        "Active": "active",  # Map 'Active' to 'status'
        "Source": "source",
        "Inactive Date": "inactive_date",
        "Fund List": "fund_list",  # Map 'Fund List' to 'fund_list'
        "Effective Date": "effective_date",  # Map 'Effective Date' to 'first_close_date'
        "Beneficial Owner Change": "beneficial_owner_change",  # Map 'Beneficial Owner Change' to 'beneficial_owner_change'
        "New LP Short Name": "new_lp_short_name",  # Map 'New LP Short Name' to 'new_lp_short_name'
        "SEI_ID_ABF": "sei_id_abf",  # Map 'SEI_ID_ABF' to 'sei_id_abf'
        "SEI_ID_SF2": "sei_id_sf2",  # Map 'SEI_ID_SF2' to 'sei_id_sf2'
    },
    "tbLPFund": {
        "LP Short Name": "lp_short_name",
        "Fund Group": "fund_group",  # Map 'Fund Group' to 'fund_group'
        "Fund": "fund_name",  # Map 'Fund' to 'fund_name'
        "Blocker": "blocker",  # Map 'Blocker' to 'blocker'
        "Term": "term",  # Map 'Term' to 'term'
        "Current ARE": "current_are",  # Map 'Current ARE' to 'current_are'
        "Term End": "term_end",  # Map 'Term End' to 'term_end'
        "ARE Start": "are_start",  # Map 'ARE Start' to 'are_start'
        "Reinvest Start": "reinvest_start",  # Map 'Reinvest Start' to 'reinvest_start'
        "Harvest Start": "harvest_start",  # Map 'Harvest Start' to 'harvest_start'
        "Inactive Date": "inactive_date",  # Map 'Inactive Date' to 'inactive_date'
        "Management Fee": "management_fee",  # Map 'Management Fee' to 'management_fee'
        "Incentive": "incentive",  # Map 'Incentive' to 'incentive'
        "Status": "status",  # Map 'Status' to 'status'
       },
    "tbPCAP": {
        "LP Short Name": "lp_short_name",
        "PCAP Date": "pcap_date",
        "Field Num": "field_num",
        "Field": "field",  # Map 'Field' to 'field'
        "Amount": "amount",  # Map 'Amount' to 'amount'
    },
    "tbLedger": {
        "Entry Date": "entry_date",
        "Activity Date": "activity_date",
        "Effective Date": "effective_date",
        "Activity": "activity",  # Map 'Activity' to 'activity'
        "Sub Activity": "sub_activity",  # Map 'Sub Activity' to 'sub_activity'
        "Amount": "amount",  # Map 'Amount' to 'amount'
        "Entity From": "entity_from",  # Map 'Entity From' to 'entity_from'
        "Entity To": "entity_to",  # Map 'Entity To' to 'entity_to'
        "Related Entity": "related_entity",  # Map 'Related Entity' to 'related_entity'
        "Related Fund": "related_fund",  # Map 'Related Fund' to 'related_fund'
        },
}

def clean_date(value):
    """Convert a value to a valid date or None."""
    try:
        return datetime.strptime(value, "%m/%d/%Y").date() if pd.notna(value) else None
    except ValueError:
        return None

def clean_percentage_to_fraction(value):
    """Convert a percentage string to a fraction (e.g., '2.00%' -> 0.02) or None."""
    try:
        return float(value.strip('%')) / 100 if pd.notna(value) else None
    except ValueError:
        return None

def clean_column(df, column_name, cleaning_type):
    """
    General function to clean a column in a DataFrame.

    Parameters:
        df (pd.DataFrame): The DataFrame containing the column to clean.
        column_name (str): The name of the column to clean.
        cleaning_type (str): The type of cleaning to apply. Options are:
            - 'remove_commas': Remove commas from the column values.
            - 'to_numeric': Convert the column values to numeric, coercing errors to NaN.
            - 'drop_na': Drop rows where the column contains NaN values.
            - 'clean_date': Convert the column values to valid dates.

    Returns:
        pd.DataFrame: The cleaned DataFrame.
    """
    if cleaning_type == 'remove_commas':
        df[column_name] = df[column_name].str.replace(",", "", regex=True)
    elif cleaning_type == 'to_numeric':
        df[column_name] = pd.to_numeric(df[column_name], errors="coerce")
    elif cleaning_type == 'drop_na':
        df = df.dropna(subset=[column_name])
    elif cleaning_type == 'clean_date':
        df[column_name] = df[column_name].apply(clean_date)
    return df

def load_csv_to_db():
    with Session(engine) as session:
        for table_name, file_path in csv_files.items():
            df = pd.read_csv(file_path)

            # Strip leading/trailing spaces from column names
            df.columns = df.columns.str.strip()

            # Rename columns if a mapping exists
            if table_name in column_mappings:
                df.rename(columns=column_mappings[table_name], inplace=True)

            # Clean date columns for tbLPLookup
            if table_name == "tbLPLookup":
                date_columns = ["inactive_date"]  # Removed 'first_close_date'
                for col in date_columns:
                    df = clean_column(df, col, 'clean_date')

            # Clean date and percentage columns for tbLPFund
            if table_name == "tbLPFund":
                date_columns = ["term_end", "are_start", "reinvest_start", "harvest_start", "inactive_date"]
                percentage_columns = ["management_fee", "incentive"]

                for col in date_columns:
                    df = clean_column(df, col, 'clean_date')

                for col in percentage_columns:
                    df[col] = df[col].apply(clean_percentage_to_fraction)

            # Clean the 'amount' column for tbPCAP
            if table_name == "tbPCAP":
                df = clean_column(df, "amount", 'remove_commas')
                df = clean_column(df, "amount", 'to_numeric')
                df = clean_column(df, "amount", 'drop_na')

            if table_name == "tbLedger":
                # Clean date columns first
                date_columns = ["entry_date", "activity_date", "effective_date"]
                for col in date_columns:
                    df = clean_column(df, col, 'clean_date')
                
                # Clean amount column
                df['amount'] = pd.to_numeric(df['amount'].str.replace(',', ''), errors='coerce')
                
                # Print detailed debugging information
                print("\nFirst 5 rows of tbLedger data:")
                debug_columns = ["entry_date", "activity_date", "effective_date", "activity", 
                                "sub_activity", "amount", "entity_from", "entity_to", 
                                "related_entity", "related_fund"]
                print(df[debug_columns].head().to_string())
                
                # Convert DataFrame to records and clean them before adding to session
                records = []
                for _, row in df.iterrows():
                    clean_record = {
                        'entry_date': row['entry_date'],
                        'activity_date': row['activity_date'],
                        'effective_date': row['effective_date'],
                        'activity': str(row['activity']),
                        'sub_activity': str(row['sub_activity']) if pd.notna(row['sub_activity']) else None,
                        'amount': float(row['amount']) if pd.notna(row['amount']) else None,
                        'entity_from': str(row['entity_from']),
                        'entity_to': str(row['entity_to']),
                        'related_entity': str(row['related_entity']),
                        'related_fund': str(row['related_fund'])
                    }
                    records.append(clean_record)
                
                # Print first record for verification
                print("\nFirst clean record:")
                print(records[0])
                
                # Add clean records to session
                for record in records:
                    session.add(tbLedger(**record))
                
                # Commit the records
                session.commit()
                print(f"Loaded data into {table_name}.")
                
                # Skip the general record creation loop
                continue
                        
            for _, row in df.iterrows():
                if table_name == "tbLPLookup":
                    # Check if the record already exists
                    existing_record = session.query(tbLPLookup).filter_by(short_name=row["short_name"]).first()
                    if existing_record:
                        # Update the existing record
                        for key, value in row.to_dict().items():
                            setattr(existing_record, key, value)
                    else:
                        # Insert a new record
                        session.add(tbLPLookup(**row.to_dict()))
                elif table_name == "tbLPFund":
                    session.add(tbLPFund(**row.to_dict()))
                elif table_name == "tbPCAP":
                    session.add(tbPCAP(**row.to_dict()))
                elif table_name == "tbLedger":
                    session.add(tbLedger(**row.to_dict()))
            session.commit()
            print(f"Loaded data into {table_name}.")

if __name__ == "__main__":
    load_csv_to_db()