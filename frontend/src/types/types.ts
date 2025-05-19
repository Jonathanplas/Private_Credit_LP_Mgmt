/**
 * Base LP information
 */
export interface LP {
    short_name: string;
    active: boolean;
    source: string;
    effective_date: string;
    inactive_date: string | null;
    fund_list: string[];
    beneficial_owner_change: boolean;
    new_lp_short_name: string | null;
    sei_id_abf: string | null;
    sei_id_sf2: string | null;
}

/**
 * Transaction data structure
 */
export interface Transaction {
    effective_date: string;
    activity: string;
    sub_activity: string | null;
    amount: number;
    entity_from: string;
    entity_to: string;
    related_fund: string;
}

/**
 * Metric with value and transactions
 */
export interface Metric {
    value: number;
    transactions: Transaction[];
}

/**
 * Extended Metric type for remaining capital with both calculation methods
 */
export interface RemainingCapitalMetric extends Metric {
    cash_based_value?: number;
    nav_based_value?: number;
    is_reinvest_active?: boolean;
}

/**
 * Financial metrics shared by both funds and LP totals
 */
export interface FinancialMetrics {
    total_commitment: Metric;
    total_capital_called: Metric;
    total_capital_distribution: Metric;
    total_income_distribution: Metric;
    total_distribution: Metric;
    remaining_capital: RemainingCapitalMetric;
}

/**
 * Individual fund information
 */
export interface Fund {
    fund_name: string;
    fund_group: string;
    status: string;
    management_fee: number;
    incentive: number;
    term_end: string;
    reinvest_start: string | null;
    harvest_start: string | null;
    metrics: FinancialMetrics;
}

/**
 * Complete LP details including funds and metrics
 */
export interface LPDetails {
    lp_details: LP;
    funds: Fund[];
    totals: FinancialMetrics;
    irr: number | null;
    irr_snapshot_data_issue: boolean;
    irr_chronology_issue: boolean;
    pcap_report_date: string | null;
}

/**
 * Props for LPDetails component
 */
export interface LPDetailsProps {
    lpShortName: string;
    reportDate: string;
}

/**
 * Props for LPSelector component
 */
export interface LPSelectorProps {
    onLPSelect: (lpShortName: string) => void;
    onDateChange: (date: string) => void;
}

/**
 * Data Management Types
 */
export interface LPLookupData {
    short_name: string;
    active: string | null;
    source: string | null;
    effective_date: string | null;
    inactive_date: string | null;
    fund_list: string | null;
    beneficial_owner_change: string | null;
    new_lp_short_name: string | null;
    sei_id_abf: string | null;
    sei_id_sf2: string | null;
}

export interface LPFundData {
    id?: number;
    lp_short_name: string;
    fund_group: string | null;
    fund_name: string;
    blocker: string | null;
    term: number | null;
    current_are: number | null;
    term_end: string | null;
    are_start: string | null;
    reinvest_start: string | null;
    harvest_start: string | null;
    inactive_date: string | null;
    management_fee: number | null;
    incentive: number | null;
    status: string | null;
}

export interface PCAPData {
    id?: number;
    lp_short_name: string;
    pcap_date: string;
    field_num: number;
    field: string;
    amount: number;
}

export interface LedgerData {
    id?: number;
    entry_date: string;
    activity_date: string;
    effective_date: string;
    activity: string;
    sub_activity: string | null;
    amount: number;
    entity_from: string;
    entity_to: string;
    related_entity: string;
    related_fund: string;
}

export type TableType = 'lplookup' | 'lpfund' | 'pcap' | 'ledger';

export interface TableProps {
    tableType: TableType;
}