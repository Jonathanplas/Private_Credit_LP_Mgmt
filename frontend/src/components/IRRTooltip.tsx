import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import config from '../config';
import './tooltip.css';

interface IRRTooltipProps {
    lpShortName: string;
    reportDate: string;
    irrSnapshotDataIssue?: boolean;
    irrChronologyIssue?: boolean;
    children?: React.ReactNode;
}

interface IRRCashFlow {
    effective_date: string;
    activity: string;
    sub_activity: string | null;
    amount: number;
    entity_from: string;
    entity_to: string;
    related_fund: string;
}

interface IRRCashFlowsResponse {
    cash_flows: IRRCashFlow[];
    irr: number | null;
    pcap_date: string | null;
    chronology_adjusted?: boolean;
    snapshot_data_issue?: boolean;
}

const IRRTooltip: React.FC<IRRTooltipProps> = ({ 
    lpShortName, 
    reportDate, 
    irrSnapshotDataIssue = false,
    irrChronologyIssue = false,
    children 
}) => {
    const [isVisible, setIsVisible] = useState(false);
    const [cashFlows, setCashFlows] = useState<IRRCashFlow[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [pcapDate, setPcapDate] = useState<string | null>(null);
    const [showBelow, setShowBelow] = useState(false);
    const [chronologyAdjusted, setChronologyAdjusted] = useState(false);
    const [snapshotDataIssue, setSnapshotDataIssue] = useState(irrSnapshotDataIssue);
    const [irrValue, setIrrValue] = useState<number | null>(null); // Added state for IRR value
    
    const tooltipRef = useRef<HTMLDivElement>(null);
    const contentRef = useRef<HTMLDivElement>(null);

    // Calculate summary values for the tooltip
    const calculateSummaries = (): { 
        totalCapitalCalls: number,
        totalDistributions: number,
        pcapEndingBalance: number | null
    } => {
        let totalCapitalCalls = 0;
        let totalDistributions = 0;
        let pcapEndingBalance = null;

        if (cashFlows && cashFlows.length > 0) {
            cashFlows.forEach(cf => {
                // Check for all types of capital contributions (standard capital calls, transfers, and PCAP capital calls)
                if (cf.activity === "Capital Call" || 
                    cf.activity === "Transfer (Capital Contribution)" ||
                    cf.activity === "Capital Call (from PCAP)") {
                    totalCapitalCalls += Math.abs(cf.amount);
                } else if (cf.activity === "LP Distribution") {
                    totalDistributions += cf.amount;
                } else if (cf.activity === "PCAP Ending Balance") {
                    pcapEndingBalance = cf.amount;
                }
            });
        }

        return { totalCapitalCalls, totalDistributions, pcapEndingBalance };
    };

    // Fetch cash flows when the tooltip is shown
    useEffect(() => {
        if (isVisible && cashFlows.length === 0 && !loading) {
            fetchIRRCashFlows();
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isVisible]);

    // Check tooltip position and adjust if needed
    useEffect(() => {
        if (isVisible && contentRef.current) {
            // Get tooltip position
            const tooltipRect = contentRef.current.getBoundingClientRect();
            
            // If tooltip is too close to top of viewport, show it below instead
            if (tooltipRect.top < 10) {
                setShowBelow(true);
            } else {
                setShowBelow(false);
            }
            
            // Make the tooltip visible after positioning is determined
            contentRef.current.style.visibility = 'visible';
            contentRef.current.style.opacity = '1';
        }
    }, [isVisible, cashFlows]);

    // Update from props
    useEffect(() => {
        setSnapshotDataIssue(irrSnapshotDataIssue);
    }, [irrSnapshotDataIssue]);

    const fetchIRRCashFlows = async () => {
        if (!lpShortName) return;
        
        try {
            setLoading(true);
            setError(null);
            const response = await axios.get<IRRCashFlowsResponse>(
                `${config.API_URL}/api/lp/${lpShortName}/irr-cash-flows?report_date=${reportDate}`
            );
            
            setCashFlows(response.data.cash_flows);
            setPcapDate(response.data.pcap_date);
            setChronologyAdjusted(response.data.chronology_adjusted || false);
            setIrrValue(response.data.irr); // Store the IRR value
            if (response.data.snapshot_data_issue !== undefined) {
                setSnapshotDataIssue(response.data.snapshot_data_issue);
            }
        } catch (err) {
            setError('Error fetching IRR data');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleMouseEnter = () => {
        setIsVisible(true);
    };

    const handleMouseLeave = (e: React.MouseEvent) => {
        // Check if the mouse is leaving to go to the tooltip content
        if (contentRef.current && e.relatedTarget instanceof Node && !contentRef.current.contains(e.relatedTarget)) {
            // Only hide the tooltip if we're not moving into the tooltip content
            setIsVisible(false);
        }
    };

    const handleContentMouseLeave = (e: React.MouseEvent) => {
        // Check if we're moving back to the tooltip icon
        if (tooltipRef.current && e.relatedTarget instanceof Node && !tooltipRef.current.contains(e.relatedTarget)) {
            // Only hide the tooltip if we're not moving back to the icon
            setIsVisible(false);
        }
    };

    const downloadCSV = () => {
        if (!cashFlows || cashFlows.length === 0) {
            console.error('No cash flows available for download.');
            alert('No cash flows available to download. Please check the data.');
            return;
        }

        console.log('Download CSV triggered');
        console.log('Cash Flows:', cashFlows);
        console.log('LP Short Name:', lpShortName);

        const headers = ['Date', 'Activity', 'Sub Activity', 'Amount', 'From', 'To', 'Fund'];
        const csvContent = [
            headers.join(','),
            ...cashFlows.map(cf => [
                cf.effective_date,
                cf.activity,
                cf.sub_activity || '',
                cf.amount,
                cf.entity_from || '',
                cf.entity_to || '',
                cf.related_fund || ''
            ].join(','))
        ].join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `irr_cash_flows_${lpShortName}.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const formatCurrency = (amount: number): string => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(amount);
    };

    const formatDate = (dateString: string): string => {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', { 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric' 
        });
    };

    const formatPercent = (value: number | null): string => {
        if (value === null) return 'N/A';
        return new Intl.NumberFormat('en-US', {
            style: 'percent',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(value);
    };

    const { totalCapitalCalls, totalDistributions, pcapEndingBalance } = calculateSummaries();

    // Find the earliest distribution date if we have a snapshot data issue
    let earliestDistribution: string | null = null;
    if (snapshotDataIssue && cashFlows && cashFlows.length > 0) {
        const distributionDates = cashFlows
            .filter(cf => cf.activity === "LP Distribution")
            .map(cf => cf.effective_date)
            .sort();
        
        if (distributionDates.length > 0) {
            earliestDistribution = distributionDates[0];
        }
    }

    // Determine the source of capital contributions
    const hasTransfers = cashFlows.some(cf => cf.activity === "Transfer (Capital Contribution)");
    const hasPcapCapitalCalls = cashFlows.some(cf => cf.activity === "Capital Call (from PCAP)");
    
    // Determine appropriate label and source description
    const capitalSourceLabel = hasTransfers ? "Capital Contribution" : "Capital Calls";
    let capitalSourceDescription = "tbLedger (activity = 'Capital Call')";
    
    if (hasTransfers) {
        capitalSourceDescription = "tbPCAP (field = 'Transfers')";
    } else if (hasPcapCapitalCalls) {
        capitalSourceDescription = "tbPCAP (field = 'Capital Calls')";
    }

    return (
        <div 
            className="tooltip-container"
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
            ref={tooltipRef}
        >
            {children || <span className="info-icon">ⓘ</span>}
            {isVisible && (
                <div 
                    className={`tooltip-content irr-tooltip ${showBelow ? 'below' : ''}`}
                    onMouseEnter={handleMouseEnter}
                    onMouseLeave={handleContentMouseLeave}
                    ref={contentRef}
                    style={{ visibility: 'hidden', opacity: 0 }}
                >
                    <div className="tooltip-text">
                        <h4>IRR Calculation Explanation</h4>
                        
                        
                        {snapshotDataIssue && (
                            <div className="snapshot-data-warning">
                                <p><strong>📊 PCAP Snapshot Data Notice</strong></p>
                                <p>The transfer amount of {formatCurrency(totalCapitalCalls)} is from a PCAP snapshot on {pcapDate ? formatDate(pcapDate) : 'the end-of-quarter'}, but distributions occurred earlier {earliestDistribution ? `(${formatDate(earliestDistribution)})` : ''}.</p>
                                <p>This is normal: PCAP contains snapshot data as of quarter-end while distributions are recorded in real-time.</p>
                            </div>
                        )}
                        
                        {chronologyAdjusted && !snapshotDataIssue && (
                            <div className="chronology-warning">
                                <p><strong>⚠️ Warning:</strong> Chronological adjustment applied</p>
                                <p>Distribution dates precede capital contributions. The system adjusted dates to ensure a valid IRR calculation.</p>
                            </div>
                        )}
                        
                        <p className="formula-section">XIRR Formula:</p>
                        <p className="formula">
                            0 = Σ [ CF<sub>i</sub> / (1 + IRR)<sup>d<sub>i</sub>/365</sup> ]
                        </p>
                        <p className="formula-explanation">Where CF<sub>i</sub> is cash flow at date d<sub>i</sub></p>
                        
                        <div className="irr-components">
                            <p><strong>{capitalSourceLabel}:</strong> {formatCurrency(-totalCapitalCalls)}</p>
                            <p className="data-source">Source: {capitalSourceDescription}</p>
                            
                            <p><strong>Distributions:</strong> {formatCurrency(totalDistributions)}</p>
                            <p className="data-source">Source: tbLedger (activity = 'LP Distribution')</p>
                            
                            <p><strong>PCAP Ending Balance ({pcapDate ? formatDate(pcapDate) : 'N/A'}):</strong> {pcapEndingBalance !== null ? formatCurrency(pcapEndingBalance) : 'N/A'}</p>
                            <p className="data-source">Source: tbPCAP (field = 'Ending Capital Balance')</p>
                        </div>
                        
                        <div className="irr-notes">
                            <p><strong>Notes:</strong></p>
                            <p>- {hasTransfers ? "Transfers" : hasPcapCapitalCalls ? "Capital calls from PCAP" : "Capital calls"} are negative flows (investor perspective)</p>
                            <p>- Management fees included in capital contributions</p>
                            <p>- Operating expenses in PCAP balance</p>
                            <p>- Excludes pending calls after {pcapDate ? formatDate(pcapDate) : 'PCAP date'}</p>
                        </div>
                    </div>
                    
                    {loading && <div className="loading">Loading cash flow data...</div>}
                    {error && <div className="error">{error}</div>}
                    
                    {cashFlows && cashFlows.length > 0 && (
                        <div className="tooltip-data">
                            <table className="data-preview">
                                <thead>
                                    <tr>
                                        <th>Date</th>
                                        <th>Activity</th>
                                        <th>Fund</th>
                                        <th>Amount</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {cashFlows.slice(0, 4).map((cf, i) => (
                                        <tr key={i}>
                                            <td>{formatDate(cf.effective_date)}</td>
                                            <td>{cf.activity}</td>
                                            <td>{cf.related_fund || 'N/A'}</td>
                                            <td>{formatCurrency(cf.amount)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                            {cashFlows.length > 4 && (
                                <div className="tooltip-footer">
                                    And {cashFlows.length - 4} more transactions...
                                </div>
                            )}
                            <button className="download-button" onClick={downloadCSV}>
                                Download IRR Cash Flows
                            </button>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default IRRTooltip;