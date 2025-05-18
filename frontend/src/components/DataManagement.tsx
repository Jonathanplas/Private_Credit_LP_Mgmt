import React, { useState } from 'react';
import { TableType } from '../types/types';
import './DataManagement.css';
import DataTable from '../components/DataTable';

/**
 * Main component for managing database tables
 */
const DataManagement: React.FC = () => {
  const [activeTable, setActiveTable] = useState<TableType>('lplookup');
  
  return (
    <div className="data-management-container">
      <h2>Database Management</h2>
      
      <div className="table-selector">
        <button 
          className={activeTable === 'lplookup' ? 'active' : ''}
          onClick={() => setActiveTable('lplookup')}
        >
          LP Lookup
        </button>
        <button 
          className={activeTable === 'lpfund' ? 'active' : ''}
          onClick={() => setActiveTable('lpfund')}
        >
          LP Fund
        </button>
        <button 
          className={activeTable === 'pcap' ? 'active' : ''}
          onClick={() => setActiveTable('pcap')}
        >
          PCAP
        </button>
        <button 
          className={activeTable === 'ledger' ? 'active' : ''}
          onClick={() => setActiveTable('ledger')}
        >
          Ledger
        </button>
      </div>
      
      <div className="table-container">
        <DataTable tableType={activeTable} />
      </div>
    </div>
  );
};

export default DataManagement;