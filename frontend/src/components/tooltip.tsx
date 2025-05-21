import React, { useState, useRef, useEffect } from 'react';
import { Transaction } from '../types/types';
import './tooltip.css';

interface TooltipProps {
    text: string;
    transactions?: Transaction[];
    metricName?: string;
    children?: React.ReactNode;
    distributionDiscrepancy?: {
        difference: number;
        otherSubcategories: Array<{
            name: string;
            amount: number;
            transactions: Transaction[];
        }>;
        otherSubcategoryNames?: string[];
    } | null;
    customTooltipContent?: React.ReactNode;
}

const Tooltip: React.FC<TooltipProps> = ({ text, transactions, metricName, children, distributionDiscrepancy, customTooltipContent }) => {
    const [isVisible, setIsVisible] = useState(false);
    const [showBelow, setShowBelow] = useState(false);
    const tooltipRef = useRef<HTMLDivElement>(null);
    const contentRef = useRef<HTMLDivElement>(null);

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
    }, [isVisible]);

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
        if (!transactions) return;

        const headers = ['Date', 'Activity', 'Sub Activity', 'Amount', 'From', 'To', 'Fund'];
        const csvContent = [
            headers.join(','),
            ...transactions.map(t => [
                t.effective_date,
                t.activity,
                t.sub_activity || '',
                t.amount,
                t.entity_from,
                t.entity_to,
                t.related_fund
            ].join(','))
        ].join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `${metricName}_transactions.csv`;
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
                    className={`tooltip-content ${showBelow ? 'below' : ''}`}
                    onMouseEnter={handleMouseEnter}
                    onMouseLeave={handleContentMouseLeave}
                    ref={contentRef}
                    style={{ visibility: 'hidden', opacity: 0 }}
                >
                    <div className="tooltip-text">
                        {text}
                        {distributionDiscrepancy && distributionDiscrepancy.otherSubcategories.length > 0 && (
                            <div className="distribution-discrepancy">
                                <p className="discrepancy-note">
                                    <span className="info-icon">ℹ️</span> 
                                    Also includes {formatCurrency(distributionDiscrepancy.difference)} 
                                    {distributionDiscrepancy.otherSubcategories.length > 0 && 
                                     ` (e.g., ${distributionDiscrepancy.otherSubcategories[0].name})`}
                                </p>
                            </div>
                        )}
                    </div>
                    {customTooltipContent}
                    {transactions && transactions.length > 0 && (
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
                                    {transactions.slice(0, 4).map((t, i) => (
                                        <tr key={i}>
                                            <td>{t.effective_date}</td>
                                            <td>{t.activity}</td>
                                            <td>{t.related_fund}</td>
                                            <td>{formatCurrency(t.amount)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                            {transactions.length > 4 && (
                                <div className="tooltip-footer">
                                    And {transactions.length - 4} more transactions...
                                </div>
                            )}
                            <button className="download-button" onClick={downloadCSV}>
                                Download Full Data
                            </button>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default Tooltip;