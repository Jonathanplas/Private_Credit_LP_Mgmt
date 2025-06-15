import React, { useState, useEffect } from "react";
import axios from "axios";
import { LPDetails as LPDetailsType, Fund, Transaction } from "../types/types";
import config from '../config';
import Tooltip from './tooltip';
import IRRTooltip from './IRRTooltip';
import './LPDetails.css';

interface LocalLPDetailsProps {
    lpShortName: string;
    reportDate: string;
}

const tooltipTexts = {
    totalCommitment: {
        text: "Total Commitment Amount as of Report Date",
        dataKey: "total_commitment"
    },
    totalCapitalCalled: {
        text: "Total Capital Called as of Report Date",
        dataKey: "total_capital_called"
    },
    totalCapitalDistribution: {
        text: "Total Capital Distribution as of Report Date",
        dataKey: "total_capital_distribution"
    },
    totalIncomeDistribution: {
        text: "Total Income Distribution as of Report Date",
        dataKey: "total_income_distribution"
    },
    totalDistribution: {
        text: "Total Distribution as of Report Date",
        dataKey: "total_distribution"
    },
    remainingCapital: {
        text: "Remaining Capital as of Report Date. This value shows the LP's most recent capital balance from their partner capital statement (PCAP), including any appreciation or depreciation of investments.",
        dataKey: "remaining_capital"
    },
    irr: {
        text: "Internal Rate of Return based on cash flows",
        dataKey: null
    },
    pcapDate: {
        text: "Most recent PCAP report date available",
        dataKey: null
    }
};

const LPDetails: React.FC<LocalLPDetailsProps> = ({ lpShortName, reportDate }) => {
    const [lpData, setLPData] = useState<LPDetailsType | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [distributionDiscrepancy, setDistributionDiscrepancy] = useState<{
        difference: number, 
        otherSubcategories: Array<{name: string, amount: number, transactions: Transaction[]}>,
        otherSubcategoryNames?: string[]
    } | null>(null);

    useEffect(() => {
        const fetchLPDetails = async () => {
            if (!lpShortName) {
                setLoading(false);
                return;
            }

            try {
                setLoading(true);
                setError(null);
                const response = await axios.get<LPDetailsType>(
                    `${config.API_URL}/api/lp/${lpShortName}?report_date=${reportDate}`
                );
                console.log('API Response:', response.data); // For debugging
                setLPData(response.data);
            } catch (err) {
                setError('Error fetching LP details');
                console.error(err);
            } finally {
                setLoading(false);
            }
        };

        fetchLPDetails();
    }, [lpShortName, reportDate]);

    const formatCurrency = (amount: number | undefined): string => {
        if (amount === undefined) return 'N/A';
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(amount);
    };

    const formatDate = (date: string | null): string => {
        if (!date) return 'N/A';
        // Parse the date parts and create the date object with local timezone
        // This prevents timezone shifts when displaying dates
        const [year, month, day] = date.split('-').map(Number);
        return new Date(year, month - 1, day).toLocaleDateString();
    };

    const getRemainingCapitalValue = (fund: Fund | null, totals = false): number => {
        if (!fund) return 0;

        const metrics = totals ? lpData?.totals : fund.metrics;
        if (!metrics) return 0;

        const remainingCapital = metrics.remaining_capital;
        
        if (remainingCapital.nav_based_value !== undefined) {
            return remainingCapital.nav_based_value;
        }
        
        // Fallback to the default value
        return remainingCapital.value;
    };

    const FundCard: React.FC<{fund: Fund}> = ({ fund }) => (
        <div className="fund-card">
            <h4>{fund.fund_name}</h4>
            <div className="fund-info">
                <div className="info-row">
                    <span className="label">Group:</span>
                    <span>{fund.fund_group}</span>
                </div>
                <div className="info-row">
                    <span className="label">Status:</span>
                    <span>{fund.status}</span>
                </div>
                <div className="info-row">
                    <span className="label">Management Fee:</span>
                    <span>{(fund.management_fee * 100).toFixed(2)}%</span>
                </div>
                <div className="info-row">
                    <span className="label">Incentive:</span>
                    <span>{(fund.incentive * 100).toFixed(2)}%</span>
                </div>
                <div className="info-row">
                    <span className="label">Term End:</span>
                    <span>{formatDate(fund.term_end)}</span>
                </div>
                {fund.reinvest_start && (
                    <div className="info-row">
                        <span className="label">Reinvest Start:</span>
                        <span>{formatDate(fund.reinvest_start)}</span>
                    </div>
                )}
                {fund.harvest_start && (
                    <div className="info-row">
                        <span className="label">Harvest Start:</span>
                        <span>{formatDate(fund.harvest_start)}</span>
                    </div>
                )}
            </div>
        </div>
    );

    const hasReinvestActiveFunds = (): boolean => {
        if (!lpData?.funds) return false;
        
        const currentDate = new Date(reportDate);
        return lpData.funds.some(fund => {
            if (!fund.reinvest_start) return false;
            
            const reinvestStartDate = new Date(fund.reinvest_start);
            const hasHarvestStarted = fund.harvest_start ? new Date(fund.harvest_start) <= currentDate : false;
            
            return reinvestStartDate <= currentDate && !hasHarvestStarted;
        });
    };

    const ReinvestmentNotification = () => (
        <div className="reinvestment-notification">
            <div className="notification-content">
                <h4>💡 Why Reinvestment + Distributions Is Not a Conflict</h4>
                <p>
                    <strong>Reinvestment = capital (principal) can be reused</strong>, but <strong>income still flows to LPs</strong> as yield.
                    This fund shows income distributions while capital remains locked and working.
                </p>
            </div>
        </div>
    );

    const getDistributionDiscrepancy = () => {
        if (!lpData?.totals) return null;
        
        const { total_distribution, total_capital_distribution, total_income_distribution } = lpData.totals;
        const sumOfParts = total_capital_distribution.value + total_income_distribution.value;
        
        if (Math.abs(total_distribution.value - sumOfParts) < 0.01) return null;
        
        const standardSubcategories = ['Capital Distribution', 'Income Distribution'];
        
        const otherSubcategoryDetails = total_distribution.transactions
            .filter(t => !standardSubcategories.includes(t.sub_activity || ''))
            .reduce((acc, t) => {
                const key = t.sub_activity || 'Uncategorized';
                if (!acc[key]) {
                    acc[key] = {
                        name: key,
                        amount: 0,
                        transactions: []
                    };
                }
                acc[key].amount += t.amount;
                acc[key].transactions.push(t);
                return acc;
            }, {} as Record<string, { name: string, amount: number, transactions: Transaction[] }>);
        
        const otherSubcategories = Object.values(otherSubcategoryDetails);
        
        return {
            difference: total_distribution.value - sumOfParts,
            otherSubcategories,
            otherSubcategoryNames: otherSubcategories.map(sc => sc.name)
        };
    };

    useEffect(() => {
        if (lpData?.totals) {
            setDistributionDiscrepancy(getDistributionDiscrepancy());
        }
    }, [lpData?.totals]);

    if (loading) return <div>Loading...</div>;
    if (error) return <div className="error">{error}</div>;
    if (!lpData) return <div>No data available</div>;

    return (
        <div className="lp-details">
            <section className="basic-info">
                <h2>{lpData.lp_details?.short_name || 'Unknown LP'}</h2>
                <div className="info-grid">
                    <div className="info-row">
                        <span className="label">Status:</span>
                        <span>{lpData.lp_details?.active ? 'Active' : 'Inactive'}</span>
                    </div>
                    <div className="info-row">
                        <span className="label">Source:</span>
                        <span>{lpData.lp_details?.source || 'N/A'}</span>
                    </div>
                    <div className="info-row">
                        <span className="label">First Close Date:</span>
                        <span>{formatDate(lpData.lp_details?.effective_date)}</span>
                    </div>
                    {lpData.lp_details?.inactive_date && (
                        <div className="info-row">
                            <span className="label">Inactive Date:</span>
                            <span>{formatDate(lpData.lp_details.inactive_date)}</span>
                        </div>
                    )}
                </div>
            </section>

            {hasReinvestActiveFunds() && <ReinvestmentNotification />}

            {lpData.totals && (
                <section className="lp-totals">
                    <h3>LP Portfolio Summary</h3>
                    <div className="totals-grid">
                        <div className="total-metrics">
                            <h4>Financial Metrics</h4>
                            <div className="metric-row">
                                <span className="metric-label">Total Commitment:</span>
                                <span className="metric-value">
                                    {formatCurrency(lpData.totals.total_commitment.value)}
                                    <Tooltip 
                                        text={tooltipTexts.totalCommitment.text}
                                        transactions={lpData.totals.total_commitment.transactions}
                                        metricName="total_commitment"
                                    />
                                </span>
                            </div>
                            <div className="metric-row">
                                <span className="metric-label">Total Capital Called:</span>
                                <span className="metric-value">
                                    {formatCurrency(lpData.totals.total_capital_called.value)}
                                    <Tooltip 
                                        text={tooltipTexts.totalCapitalCalled.text}
                                        transactions={lpData.totals.total_capital_called.transactions}
                                        metricName="total_capital_called"
                                    />
                                </span>
                            </div>
                            <div className="metric-row">
                                <span className="metric-label">Total Capital Distribution:</span>
                                <span className="metric-value">
                                    {formatCurrency(lpData.totals.total_capital_distribution.value)}
                                    <Tooltip 
                                        text={tooltipTexts.totalCapitalDistribution.text}
                                        transactions={lpData.totals.total_capital_distribution.transactions}
                                        metricName="total_capital_distribution"
                                    />
                                </span>
                            </div>
                            <div className="metric-row">
                                <span className="metric-label">Total Income Distribution:</span>
                                <span className="metric-value">
                                    {formatCurrency(lpData.totals.total_income_distribution.value)}
                                    <Tooltip 
                                        text={tooltipTexts.totalIncomeDistribution.text}
                                        transactions={lpData.totals.total_income_distribution.transactions}
                                        metricName="total_income_distribution"
                                    />
                                </span>
                            </div>
                            <div className="metric-row">
                                <span className="metric-label">Total Distribution:</span>
                                <span className="metric-value">
                                    {formatCurrency(lpData.totals.total_distribution.value)}
                                    <Tooltip 
                                        text={tooltipTexts.totalDistribution.text}
                                        transactions={lpData.totals.total_distribution.transactions}
                                        metricName="total_distribution"
                                        distributionDiscrepancy={distributionDiscrepancy}
                                    />
                                </span>
                            </div>
                            <div className="metric-row">
                                <span className="metric-label">Remaining Capital:</span>
                                <span className="metric-value">
                                    {formatCurrency(lpData.totals.remaining_capital.nav_based_value)}
                                    <Tooltip 
                                        text={tooltipTexts.remainingCapital.text}
                                        metricName="remaining_capital"
                                        customTooltipContent={
                                            <div className="pcap-balance-info">
                                                <p><strong>PCAP Ending Balance Information:</strong></p>
                                                <p>Date: {formatDate(lpData.pcap_report_date)}</p>
                                                <p>Capital Balance: {formatCurrency(lpData.totals.remaining_capital.nav_based_value)}</p>
                                                <p className="note">This value represents the LP's ownership stake in the fund assets as reported on the partner capital statement, including all unrealized gains/losses and accrued items.</p>
                                            </div>
                                        }
                                    />
                                </span>
                            </div>
                        </div>
                        <div className="irr-info">
                            <h4>IRR Information</h4>
                            <div className="metric-row">
                                <span className="metric-label">IRR:</span>
                                <span className="metric-value">
                                    {lpData.irr !== null ? `${(lpData.irr * 100).toFixed(2)}%` : 'N/A'}
                                    <IRRTooltip 
                                        lpShortName={lpShortName} 
                                        reportDate={reportDate} 
                                        irrSnapshotDataIssue={lpData.irr_snapshot_data_issue}
                                        irrChronologyIssue={lpData.irr_chronology_issue}
                                    />
                                </span>
                            </div>
                            <div className="metric-row">
                                <span className="metric-label">PCAP Report Date:</span>
                                <span className="metric-value">
                                    {formatDate(lpData.pcap_report_date)}
                                    <Tooltip text={tooltipTexts.pcapDate.text} />
                                </span>
                            </div>
                        </div>
                    </div>
                </section>
            )}

            {lpData.funds && lpData.funds.length > 0 && (
                <section className="funds-list">
                    <h3>Fund Investments</h3>
                    <div className="funds-grid">
                        {lpData.funds.map((fund, index) => (
                            <FundCard key={index} fund={fund} />
                        ))}
                    </div>
                </section>
            )}
        </div>
    );
};

export default LPDetails;