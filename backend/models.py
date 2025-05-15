from sqlalchemy import Column, String, Date, Float, Integer, ForeignKey
from backend.db import Base  # Use absolute import

class tbLPLookup(Base):
    __tablename__ = "tbLPLookup"

    short_name = Column(String, primary_key=True)
    active = Column(String)
    source = Column(String)
    effective_date = Column(Date)
    inactive_date = Column(Date)
    fund_list = Column(String)  # Add this attribute to match the CSV column
    beneficial_owner_change = Column(String)  # Add this attribute to match the CSV column
    new_lp_short_name = Column(String)  # Add this attribute to match the CSV column
    sei_id_abf = Column(String)  # Add this attribute to match the CSV column
    sei_id_sf2 = Column(String)  # Add this attribute to match the `SEI_ID_SF2` column in the CSV file

class tbLPFund(Base):
    __tablename__ = "tbLPFund"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lp_short_name = Column(String, ForeignKey("tbLPLookup.short_name"))  # Matches 'LP Short Name' in tbLPFund.csv
    fund_group = Column(String)  # Matches 'Fund Group' in tbLPFund.csv
    fund_name = Column(String)  # Matches 'Fund' in tbLPFund.csv
    blocker = Column(String)  # Matches 'Blocker' in tbLPFund.csv
    term = Column(Integer)  # Matches 'Term' in tbLPFund.csv
    current_are = Column(Integer)  # Matches 'Current ARE' in tbLPFund.csv
    term_end = Column(Date)  # Matches 'Term End' in tbLPFund.csv
    are_start = Column(Date)  # Matches 'ARE Start' in tbLPFund.csv
    reinvest_start = Column(Date)  # Matches 'Reinvest Start' in tbLPFund.csv
    harvest_start = Column(Date)  # Matches 'Harvest Start' in tbLPFund.csv
    inactive_date = Column(Date)  # Matches 'Inactive Date' in tbLPFund.csv
    management_fee = Column(Float)  # Matches 'Management Fee' in tbLPFund.csv
    incentive = Column(Float)  # Matches 'Incentive' in tbLPFund.csv
    status = Column(String)  # Matches 'Status' in tbLPFund.csv

class tbPCAP(Base):
    __tablename__ = "tbPCAP"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lp_short_name = Column(String, ForeignKey("tbLPLookup.short_name"))  # Matches 'LP Short Name' in tbPCAP.csv
    pcap_date = Column(Date)  # Matches 'PCAP Date' in tbPCAP.csv
    field_num = Column(Integer)  # Matches 'Field Num' in tbPCAP.csv
    field = Column(String)  # Matches 'Field' in tbPCAP.csv
    amount = Column(Float)  # Matches 'Amount' in tbPCAP.csv

class tbLedger(Base):
    __tablename__ = "tbLedger"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_date = Column(Date)  # Matches 'Entry Date' in tbLedger.csv
    activity_date = Column(Date)  # Matches 'Activity Date' in tbLedger.csv
    effective_date = Column(Date)  # Matches 'Effective Date' in tbLedger.csv
    activity = Column(String)  # Matches 'Activity' in tbLedger.csv
    sub_activity = Column(String, nullable=True)  # Matches 'Sub Activity' in tbLedger.csv
    amount = Column(Float)  # Matches 'Amount' in tbLedger.csv
    entity_from = Column(String)  # Matches 'Entity From' in tbLedger.csv
    entity_to = Column(String)  # Matches 'Entity To' in tbLedger.csv
    related_entity = Column(String)  # Matches 'Related Entity' in tbLedger.csv
    related_fund = Column(String)  # Matches 'Related Fund' in tbLedger.csv