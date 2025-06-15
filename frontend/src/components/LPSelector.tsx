import React, { useState, useEffect } from "react";
import axios from "axios";
import { LP } from "../types/types";
import config from '../config';
import './LPSelector.css';

interface LPSelectorProps {
    onLPSelect: (lpShortName: string) => void;
    onDateChange: (date: string) => void;
}

const LPSelector: React.FC<LPSelectorProps> = ({ onLPSelect, onDateChange }) => {
    const [lpList, setLPList] = useState<LP[]>([]);
    const [selectedLP, setSelectedLP] = useState<string>("");
    const [reportDate, setReportDate] = useState<string>(new Date().toISOString().split("T")[0]);

    useEffect(() => {
        const fetchLPs = async () => {
            try {
                const response = await axios.get<LP[]>(`${config.API_URL}/api/lps`);
                setLPList(response.data);
            } catch (error) {
                console.error("Failed to fetch LPs:", error);
            }
        };
        fetchLPs();
    }, []);

    const handleLPChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        setSelectedLP(e.target.value);
        onLPSelect(e.target.value);
    };

    const handleDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setReportDate(e.target.value);
        onDateChange(e.target.value);
    };

    return (
        <div className="lp-selector">
            <div className="select-group">
                <label htmlFor="lp-select">Select LP:</label>
                <select 
                    id="lp-select"
                    value={selectedLP} 
                    onChange={handleLPChange}
                >
                    <option value="">Select an LP...</option>
                    {lpList.map((lp) => (
                        <option key={lp.short_name} value={lp.short_name}>
                            {lp.short_name}
                        </option>
                    ))}
                </select>
            </div>

            <div className="date-group">
                <label htmlFor="report-date">Report Date:</label>
                <input
                    id="report-date"
                    type="date"
                    value={reportDate}
                    onChange={handleDateChange}
                    max={new Date().toISOString().split("T")[0]}
                />
            </div>
        </div>
    );
};

export default LPSelector;