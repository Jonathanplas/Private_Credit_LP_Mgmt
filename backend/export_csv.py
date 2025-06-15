import pandas as pd
import os
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

# Define reverse column mappings (database column name to CSV column name)
reverse_column_mappings = {
    "tbLPLookup": {
        "short_name": "LP Short Name",
        "active": "Active",
        "source": "Source",
        "inactive_date": "Inactive Date",
        "fund_list": "Fund List",
        "effective_date": "Effective Date",
        "beneficial_owner_change": "Beneficial Owner Change",
        "new_lp_short_name": "New LP Short Name",
        "sei_id_abf": "SEI_ID_ABF",
        "sei_id_sf2": "SEI_ID_SF2",
    },
    "tbLPFund": {
        "lp_short_name": "LP Short Name",
        "fund_group": "Fund Group",
        "fund_name": "Fund",
        "blocker": "Blocker",
        "term": "Term",
        "current_are": "Current ARE",
        "term_end": "Term End",
        "are_start": "ARE Start",
        "reinvest_start": "Reinvest Start",
        "harvest_start": "Harvest Start",
        "inactive_date": "Inactive Date",
        "management_fee": "Management Fee",
        "incentive": "Incentive",
        "status": "Status",
    },
    "tbPCAP": {
        "lp_short_name": "LP Short Name",
        "pcap_date": "PCAP Date",
        "field_num": "Field Num",
        "field": "Field",
        "amount": "Amount",
    },
    "tbLedger": {
        "entry_date": "Entry Date",
        "activity_date": "Activity Date",
        "effective_date": "Effective Date",
        "activity": "Activity",
        "sub_activity": "Sub Activity",
        "amount": "Amount",
        "entity_from": "Entity From",
        "entity_to": "Entity To",
        "related_entity": "Related Entity",
        "related_fund": "Related Fund",
    },
}

def format_date(date_obj):
    """Format a date object to MM/DD/YYYY format."""
    if date_obj is None:
        return None
    return date_obj.strftime("%m/%d/%Y")

def format_percentage(value):
    """Format a decimal value to percentage (e.g., 0.02 -> '2.00%')."""
    if value is None:
        return None
    return f"{value * 100:.2f}%"

def export_db_to_csv():
    """Export data from the database to CSV files."""
    with Session(engine) as session:
        # Export tbLPLookup
        lplookup_records = session.query(tbLPLookup).all()
        lplookup_data = []
        for record in lplookup_records:
            row = {
                "LP Short Name": record.short_name,
                "Active": record.active,
                "Source": record.source,
                "Effective Date": format_date(record.effective_date),
                "Inactive Date": format_date(record.inactive_date),
                "Fund List": record.fund_list,
                "Beneficial Owner Change": record.beneficial_owner_change,
                "New LP Short Name": record.new_lp_short_name,
                "SEI_ID_ABF": record.sei_id_abf,
                "SEI_ID_SF2": record.sei_id_sf2,
            }
            lplookup_data.append(row)
        
        lplookup_df = pd.DataFrame(lplookup_data)
        lplookup_df.to_csv(csv_files["tbLPLookup"], index=False)
        print(f"Exported data to {csv_files['tbLPLookup']}")
        
        # Export tbLPFund
        lpfund_records = session.query(tbLPFund).all()
        lpfund_data = []
        for record in lpfund_records:
            row = {
                "LP Short Name": record.lp_short_name,
                "Fund Group": record.fund_group,
                "Fund": record.fund_name,
                "Blocker": record.blocker,
                "Term": record.term,
                "Current ARE": record.current_are,
                "Term End": format_date(record.term_end),
                "ARE Start": format_date(record.are_start),
                "Reinvest Start": format_date(record.reinvest_start),
                "Harvest Start": format_date(record.harvest_start),
                "Inactive Date": format_date(record.inactive_date),
                "Management Fee": format_percentage(record.management_fee),
                "Incentive": format_percentage(record.incentive),
                "Status": record.status,
            }
            lpfund_data.append(row)
        
        lpfund_df = pd.DataFrame(lpfund_data)
        lpfund_df.to_csv(csv_files["tbLPFund"], index=False)
        print(f"Exported data to {csv_files['tbLPFund']}")
        
        # Export tbPCAP
        pcap_records = session.query(tbPCAP).all()
        pcap_data = []
        for record in pcap_records:
            row = {
                "LP Short Name": record.lp_short_name,
                "PCAP Date": format_date(record.pcap_date),
                "Field Num": record.field_num,
                "Field": record.field,
                "Amount": record.amount,
            }
            pcap_data.append(row)
        
        pcap_df = pd.DataFrame(pcap_data)
        pcap_df.to_csv(csv_files["tbPCAP"], index=False)
        print(f"Exported data to {csv_files['tbPCAP']}")
        
        # Export tbLedger
        ledger_records = session.query(tbLedger).all()
        ledger_data = []
        for record in ledger_records:
            row = {
                "Entry Date": format_date(record.entry_date),
                "Activity Date": format_date(record.activity_date),
                "Effective Date": format_date(record.effective_date),
                "Activity": record.activity,
                "Sub Activity": record.sub_activity,
                "Amount": record.amount,
                "Entity From": record.entity_from,
                "Entity To": record.entity_to,
                "Related Entity": record.related_entity,
                "Related Fund": record.related_fund,
            }
            ledger_data.append(row)
        
        ledger_df = pd.DataFrame(ledger_data)
        ledger_df.to_csv(csv_files["tbLedger"], index=False)
        print(f"Exported data to {csv_files['tbLedger']}")

def export_table_to_csv(table_name):
    """Export a specific table from the database to CSV."""
    if table_name not in csv_files:
        print(f"Error: Table {table_name} not found.")
        return False
    
    with Session(engine) as session:
        if table_name == "tbLPLookup":
            records = session.query(tbLPLookup).all()
            data = []
            for record in records:
                row = {
                    "LP Short Name": record.short_name,
                    "Active": record.active,
                    "Source": record.source,
                    "Effective Date": format_date(record.effective_date),
                    "Inactive Date": format_date(record.inactive_date),
                    "Fund List": record.fund_list,
                    "Beneficial Owner Change": record.beneficial_owner_change,
                    "New LP Short Name": record.new_lp_short_name,
                    "SEI_ID_ABF": record.sei_id_abf,
                    "SEI_ID_SF2": record.sei_id_sf2,
                }
                data.append(row)
        elif table_name == "tbLPFund":
            records = session.query(tbLPFund).all()
            data = []
            for record in records:
                row = {
                    "LP Short Name": record.lp_short_name,
                    "Fund Group": record.fund_group,
                    "Fund": record.fund_name,
                    "Blocker": record.blocker,
                    "Term": record.term,
                    "Current ARE": record.current_are,
                    "Term End": format_date(record.term_end),
                    "ARE Start": format_date(record.are_start),
                    "Reinvest Start": format_date(record.reinvest_start),
                    "Harvest Start": format_date(record.harvest_start),
                    "Inactive Date": format_date(record.inactive_date),
                    "Management Fee": format_percentage(record.management_fee),
                    "Incentive": format_percentage(record.incentive),
                    "Status": record.status,
                }
                data.append(row)
        elif table_name == "tbPCAP":
            records = session.query(tbPCAP).all()
            data = []
            for record in records:
                row = {
                    "LP Short Name": record.lp_short_name,
                    "PCAP Date": format_date(record.pcap_date),
                    "Field Num": record.field_num,
                    "Field": record.field,
                    "Amount": record.amount,
                }
                data.append(row)
        elif table_name == "tbLedger":
            records = session.query(tbLedger).all()
            data = []
            for record in records:
                row = {
                    "Entry Date": format_date(record.entry_date),
                    "Activity Date": format_date(record.activity_date),
                    "Effective Date": format_date(record.effective_date),
                    "Activity": record.activity,
                    "Sub Activity": record.sub_activity,
                    "Amount": record.amount,
                    "Entity From": record.entity_from,
                    "Entity To": record.entity_to,
                    "Related Entity": record.related_entity,
                    "Related Fund": record.related_fund,
                }
                data.append(row)
        
        df = pd.DataFrame(data)
        df.to_csv(csv_files[table_name], index=False)
        print(f"Exported data to {csv_files[table_name]}")
        return True

if __name__ == "__main__":
    export_db_to_csv()