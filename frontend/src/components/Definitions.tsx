import React from 'react';
import './Definitions.css';

const Definitions: React.FC = () => {
    return (
        <div className="definitions-container">
            <h1>Financial Terms Glossary</h1>
            <p className="glossary-intro">
                This glossary provides definitions for financial terms used throughout the LP Management application.
                Understanding these terms is essential for proper interpretation of the data and metrics presented.
            </p>

            <div className="definitions-section">
                <h2>Limited Partner (LP) Terms</h2>
                
                <div className="definition-item">
                    <h3>LP (Limited Partner)</h3>
                    <p>An investor in a private equity, venture capital, or hedge fund who contributes capital but has limited liability and is not involved in day-to-day management of the fund.</p>
                </div>

                <div className="definition-item">
                    <h3>Status</h3>
                    <p>Indicates whether an LP is currently Active or Inactive in the fund.</p>
                </div>

                <div className="definition-item">
                    <h3>Source</h3>
                    <p>The origin or channel through which the LP was introduced to the fund.</p>
                </div>

                <div className="definition-item">
                    <h3>First Close Date</h3>
                    <p>The date when the LP's initial investment agreement was finalized.</p>
                </div>

                <div className="definition-item">
                    <h3>Inactive Date</h3>
                    <p>The date when the LP's status was changed from Active to Inactive.</p>
                </div>
            </div>

            <div className="definitions-section">
                <h2>Fund Terms</h2>
                
                <div className="definition-item">
                    <h3>Fund Group</h3>
                    <p>The parent fund classification to which individual funds belong (e.g., ABF is a parent fund to ABF21, ABF22, etc.).</p>
                </div>

                <div className="definition-item">
                    <h3>Reinvest Start</h3>
                    <p>The date when the fund enters the reinvestment phase, allowing capital returned from investments to be redeployed into new opportunities rather than being distributed to investors. During this phase, while capital is reinvested, income distributions may still occur.</p>
                </div>

                <div className="definition-item">
                    <h3>Harvest Start</h3>
                    <p>The date when the fund enters the harvesting phase, during which the focus shifts from making new investments to realizing returns on existing investments. After this date, capital returned from investments is distributed to investors rather than being reinvested. This marks the end of the reinvestment phase.</p>
                </div>

                <div className="definition-item">
                    <h3>Term End</h3>
                    <p>The contractual end date of the fund, by which time the fund's investments should be wound up and final distributions made to LPs.</p>
                </div>

                <div className="definition-item">
                    <h3>Management Fee</h3>
                    <p>The percentage fee charged by the fund manager for managing the fund's investments, typically calculated on committed or invested capital.</p>
                </div>

                <div className="definition-item">
                    <h3>Incentive Fee</h3>
                    <p>The percentage of profits that fund managers receive as compensation for generating positive returns, also known as carried interest or performance fee.</p>
                </div>
            </div>

            <div className="definitions-section">
                <h2>Financial Metrics</h2>
                
                <div className="definition-item">
                    <h3>Total Commitment</h3>
                    <p>The total amount of capital that an LP has legally committed to provide to the fund, regardless of whether it has been called yet.</p>
                </div>

                <div className="definition-item">
                    <h3>Total Capital Called</h3>
                    <p>The cumulative amount of capital that the fund has requested from an LP to date, also known as drawn capital or paid-in capital.</p>
                </div>

                <div className="definition-item">
                    <h3>Capital Distribution</h3>
                    <p>The return of originally invested capital (principal) to the LP. This represents a return of the LP's investment, not a profit.</p>
                </div>

                <div className="definition-item">
                    <h3>Income Distribution</h3>
                    <p>The distribution of profits generated from investments to the LP, such as interest, dividends, or realized capital gains.</p>
                </div>

                <div className="definition-item">
                    <h3>Total Distribution</h3>
                    <p>The sum of both Capital Distributions and Income Distributions made to the LP.</p>
                </div>

                <div className="definition-item">
                    <h3>Remaining Capital</h3>
                    <p>The amount of an LP's capital still invested in the fund. This can be calculated in two ways:</p>
                    <ul>
                        <li><strong>Cash-Based (Called Amount – Capital Distribution)</strong>: A conservative measurement that only tracks the flow of capital called and returned, without considering appreciation or depreciation.</li>
                        <li><strong>NAV-Based (PCAP Ending Capital Balance)</strong>: Reflects the current fair market value of the LP's investment, including any appreciation or depreciation. This method is typically used for funds in the reinvestment phase.</li>
                    </ul>
                </div>

                <div className="definition-item">
                    <h3>IRR (Internal Rate of Return)</h3>
                    <p>A metric used to estimate the profitability of investments, representing the annualized effective compounded return rate. The IRR calculation includes all cash flows (Capital Calls as negative flows, Distributions as positive flows) and the current Ending Capital Balance as of the PCAP Report Date.</p>
                </div>

                <div className="definition-item">
                    <h3>XIRR</h3>
                    <p>A variation of IRR that allows for irregular cash flow timing. The application calculates IRR using the same method as Microsoft Excel's XIRR function.</p>
                </div>
            </div>

            <div className="definitions-section">
                <h2>Report Dates and Data Sources</h2>
                
                <div className="definition-item">
                    <h3>Report Date</h3>
                    <p>The user-selected date for which financial data is displayed. This cannot be later than the current date.</p>
                </div>

                <div className="definition-item">
                    <h3>PCAP Report Date</h3>
                    <p>The most recent fiscal quarter end date available in the data that is equal to or less than the Report Date. PCAP data represents the official quarterly snapshot of capital activity.</p>
                </div>

                <div className="definition-item">
                    <h3>tbLPLookup</h3>
                    <p>The data table containing unique LP (investor) names and descriptive information.</p>
                </div>

                <div className="definition-item">
                    <h3>tbLPFund</h3>
                    <p>The data table showing the funds in which the LP is an investor along with investment details.</p>
                </div>

                <div className="definition-item">
                    <h3>tbPCAP</h3>
                    <p>The data table showing each investor's capital activity at the end of each fiscal quarter, including Ending Capital Balances.</p>
                </div>

                <div className="definition-item">
                    <h3>tbLedger</h3>
                    <p>The data table showing daily cash and non-cash activities related to each LP, including Capital Calls and Distributions.</p>
                </div>
            </div>

            <div className="definitions-section">
                <h2>Reinvestment Phase Concepts</h2>
                
                <div className="definition-item">
                    <h3>Reinvestment Phase</h3>
                    <p>The period between Reinvest Start and Harvest Start dates when capital returned from investments can be redeployed rather than distributed to investors. This phase allows fund managers to continue growing the fund's assets through reinvestment.</p>
                </div>

                <div className="definition-item">
                    <h3>Reinvestment + Distributions</h3>
                    <p>During the reinvestment phase, capital (principal) can be reused for new investments, while income generated still flows to LPs as yield. This is why a fund in reinvestment phase may show income distributions even though capital remains locked and working.</p>
                </div>

                <div className="definition-item">
                    <h3>Harvesting Phase</h3>
                    <p>The period after the Harvest Start date when the fund shifts focus from making new investments to realizing returns on existing investments and returning capital to investors.</p>
                </div>
            </div>
        </div>
    );
};

export default Definitions;