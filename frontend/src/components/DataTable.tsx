import React, { useState, useEffect } from 'react';
import { TableProps, LPLookupData, LPFundData, PCAPData, LedgerData } from '../types/types';
import './DataTable.css';

// Define the API base URL
const API_BASE_URL = 'http://localhost:8000';

type DataType = LPLookupData | LPFundData | PCAPData | LedgerData;

/**
 * Component for displaying and managing table data
 */
const DataTable: React.FC<TableProps> = ({ tableType }) => {
  const [data, setData] = useState<DataType[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [editingItem, setEditingItem] = useState<DataType | null>(null);
  const [newItem, setNewItem] = useState<boolean>(false);
  const [exportStatus, setExportStatus] = useState<string | null>(null);
  
  // Function to fetch data from the API
  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/data/${tableType}`);
      if (!response.ok) {
        throw new Error(`Error fetching ${tableType} data: ${response.statusText}`);
      }
      const result = await response.json();
      setData(result);
    } catch (err) {
      setError(`Failed to load data: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setLoading(false);
    }
  };
  
  // Load data when the tableType changes
  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tableType]); // We intentionally omit fetchData to prevent infinite loops
  
  // Reset new item data when tableType changes
  useEffect(() => {
    setNewItemData(getNewItemTemplate());
    setNewItem(false);
    setEditingItem(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tableType]); // We intentionally omit getNewItemTemplate to prevent unnecessary re-renders

  // Function to create a new item
  const handleCreateItem = async (item: DataType) => {
    try {
      // Format data properly before sending to API
      const formattedItem = formatItemForSubmission(item);
      
      const response = await fetch(`${API_BASE_URL}/api/data/${tableType}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formattedItem),
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(`Error creating item (${response.status}): ${errorData?.detail || response.statusText}`);
      }
      
      // Refresh the data after creating
      fetchData();
      setNewItem(false);
    } catch (err) {
      setError(`Failed to create item: ${err instanceof Error ? err.message : String(err)}`);
    }
  };
  
  // Function to update an existing item
  const handleUpdateItem = async (item: DataType) => {
    try {
      // For lplookup, use short_name as the identifier, otherwise use id
      const idKey = tableType === 'lplookup' ? 'short_name' : 'id';
      const idValue = (item as any)[idKey];
      
      // Format data properly before sending to API
      const formattedItem = formatItemForSubmission(item);
      
      const response = await fetch(`${API_BASE_URL}/api/data/${tableType}/${idValue}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formattedItem),
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(`Error updating item (${response.status}): ${errorData?.detail || response.statusText}`);
      }
      
      // Refresh the data after updating
      fetchData();
      setEditingItem(null);
    } catch (err) {
      setError(`Failed to update item: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  // Function to delete an existing item
  const handleDeleteItem = async (item: DataType) => {
    try {
      // Get the ID or short_name based on the table type
      const idKey = tableType === 'lplookup' ? 'short_name' : 'id';
      const idValue = (item as any)[idKey];

      // Confirm deletion
      if (!window.confirm(`Are you sure you want to delete this ${tableType} item?`)) {
        return;
      }

      const response = await fetch(`${API_BASE_URL}/api/data/${tableType}/${idValue}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error(`Error deleting item: ${response.statusText}`);
      }

      // Refresh the data after deleting
      fetchData();
    } catch (err) {
      setError(`Failed to delete item: ${err instanceof Error ? err.message : String(err)}`);
    }
  };
  
  // Format an item for API submission
  const formatItemForSubmission = (item: DataType): DataType => {
    const formattedItem = { ...item };
    
    // Handle specific formatting for lpfund table
    if (tableType === 'lpfund') {
      const lpfundItem = formattedItem as LPFundData;
      
      // Ensure term and current_are are numbers, not strings
      if (lpfundItem.term !== undefined && lpfundItem.term !== null) {
        lpfundItem.term = Number(lpfundItem.term);
        // If conversion results in NaN, set to null
        if (isNaN(lpfundItem.term)) lpfundItem.term = null;
      }
      
      if (lpfundItem.current_are !== undefined && lpfundItem.current_are !== null) {
        lpfundItem.current_are = Number(lpfundItem.current_are);
        if (isNaN(lpfundItem.current_are)) lpfundItem.current_are = null;
      }
      
      // Ensure management_fee and incentive are numbers, not strings
      if (lpfundItem.management_fee !== undefined && lpfundItem.management_fee !== null) {
        lpfundItem.management_fee = Number(lpfundItem.management_fee);
        if (isNaN(lpfundItem.management_fee)) lpfundItem.management_fee = null;
      }
      
      if (lpfundItem.incentive !== undefined && lpfundItem.incentive !== null) {
        lpfundItem.incentive = Number(lpfundItem.incentive);
        if (isNaN(lpfundItem.incentive)) lpfundItem.incentive = null;
      }
      
      // Convert empty strings to null for all string fields
      Object.keys(lpfundItem).forEach(key => {
        const value = (lpfundItem as any)[key];
        if (value === '') {
          (lpfundItem as any)[key] = null;
        }
      });
      
      // Ensure date fields are formatted properly
      const dateFields = ['term_end', 'are_start', 'reinvest_start', 'harvest_start', 'inactive_date'];
      dateFields.forEach(dateField => {
        const value = (lpfundItem as any)[dateField];
        if (value && typeof value === 'string' && !value.match(/^\d{4}-\d{2}-\d{2}$/)) {
          try {
            // Try to convert string date to ISO format
            const date = new Date(value);
            if (!isNaN(date.getTime())) {
              (lpfundItem as any)[dateField] = date.toISOString().split('T')[0];
            } else {
              (lpfundItem as any)[dateField] = null;
            }
          } catch (e) {
            console.error(`Failed to parse date for ${dateField}`, e);
            (lpfundItem as any)[dateField] = null;
          }
        }
      });
    }
    
    // Handle specific formatting for pcap table
    if (tableType === 'pcap') {
      const pcapItem = formattedItem as PCAPData;
      if (pcapItem.field_num !== null) {
        pcapItem.field_num = Number(pcapItem.field_num);
        if (isNaN(pcapItem.field_num)) pcapItem.field_num = 0;
      }
      if (pcapItem.amount !== null) {
        pcapItem.amount = Number(pcapItem.amount);
        if (isNaN(pcapItem.amount)) pcapItem.amount = 0;
      }
      
      // Format pcap_date properly - fixed to use typeof check instead of instanceof
      if (pcapItem.pcap_date && typeof pcapItem.pcap_date === 'string' && !pcapItem.pcap_date.match(/^\d{4}-\d{2}-\d{2}$/)) {
        try {
          const date = new Date(pcapItem.pcap_date);
          if (!isNaN(date.getTime())) {
            pcapItem.pcap_date = date.toISOString().split('T')[0];
          }
        } catch (e) {
          console.error('Failed to parse pcap_date', e);
        }
      }
    }
    
    // Handle specific formatting for ledger table
    if (tableType === 'ledger') {
      const ledgerItem = formattedItem as LedgerData;
      if (ledgerItem.amount !== null) {
        ledgerItem.amount = Number(ledgerItem.amount);
        if (isNaN(ledgerItem.amount)) ledgerItem.amount = 0;
      }
      
      // Format date fields properly
      const dateFields = ['entry_date', 'activity_date', 'effective_date'];
      dateFields.forEach(dateField => {
        const value = (ledgerItem as any)[dateField];
        if (value && typeof value === 'string' && !value.match(/^\d{4}-\d{2}-\d{2}$/)) {
          try {
            const date = new Date(value);
            if (!isNaN(date.getTime())) {
              (ledgerItem as any)[dateField] = date.toISOString().split('T')[0];
            }
          } catch (e) {
            console.error(`Failed to parse date for ${dateField}`, e);
          }
        }
      });
    }
    
    return formattedItem;
  };
  
  // Function to get a new item template based on the tableType
  const getNewItemTemplate = (): DataType => {
    switch (tableType) {
      case 'lplookup':
        return {
          short_name: '',
          active: null,
          source: null,
          effective_date: null,
          inactive_date: null,
          fund_list: null,
          beneficial_owner_change: null,
          new_lp_short_name: null,
          sei_id_abf: null,
          sei_id_sf2: null,
        };
      case 'lpfund':
        return {
          lp_short_name: '',
          fund_group: null,
          fund_name: '',
          blocker: null,
          term: null,
          current_are: null,
          term_end: null,
          are_start: null,
          reinvest_start: null,
          harvest_start: null,
          inactive_date: null,
          management_fee: null,
          incentive: null,
          status: null,
        };
      case 'pcap':
        return {
          lp_short_name: '',
          pcap_date: new Date().toISOString().split('T')[0],
          field_num: 0,
          field: '',
          amount: 0,
        };
      case 'ledger':
        return {
          entry_date: new Date().toISOString().split('T')[0],
          activity_date: new Date().toISOString().split('T')[0],
          effective_date: new Date().toISOString().split('T')[0],
          activity: '',
          sub_activity: null,
          amount: 0,
          entity_from: '',
          entity_to: '',
          related_entity: '',
          related_fund: '',
        };
      default:
        return {} as DataType;
    }
  };
  
  // Function to render the form for creating or editing an item
  const renderForm = (item: DataType, isNew: boolean) => {
    const handleSubmit = (e: React.FormEvent) => {
      e.preventDefault();
      if (isNew) {
        handleCreateItem(item);
      } else {
        handleUpdateItem(item);
      }
    };
    
    // Get the keys of the item to render form fields
    const keys = Object.keys(item);
    
    return (
      <form onSubmit={handleSubmit} className="data-form">
        <h3>{isNew ? 'Create New Item' : 'Edit Item'}</h3>
        
        {keys.map((key) => {
          // Skip rendering the id field for new items
          if (key === 'id' && isNew) return null;
          
          // Get the current value
          const value = (item as any)[key];
          
          // Determine the input type
          let inputType = 'text';
          
          if (key.includes('date')) {
            inputType = 'date';
          } else if (key === 'term' || key === 'current_are' || key === 'field_num') {
            inputType = 'number';
            // Use integer step for these fields
          } else if (key === 'amount' || key === 'management_fee' || key === 'incentive') {
            inputType = 'number';
            // Use decimal step for these fields
          }
          
          // Render the appropriate input field
          return (
            <div key={key} className="form-group">
              <label htmlFor={key}>{key}:</label>
              {inputType === 'date' ? (
                <input
                  type="date"
                  id={key}
                  value={value || ''}
                  onChange={(e) => {
                    const newItem = { ...item, [key]: e.target.value || null };
                    isNew ? setNewItemData(newItem) : setEditingItem(newItem);
                  }}
                  required={key === 'pcap_date' || key === 'entry_date' || key === 'activity_date' || key === 'effective_date'}
                />
              ) : inputType === 'number' ? (
                <input
                  type="number"
                  id={key}
                  step={key === 'amount' || key === 'management_fee' || key === 'incentive' ? "0.01" : "1"}
                  value={value === null ? '' : value}
                  onChange={(e) => {
                    // For number fields, store empty strings as null, otherwise as proper numbers
                    const newValue = e.target.value === '' ? null : 
                      (key === 'amount' || key === 'management_fee' || key === 'incentive') ? 
                        parseFloat(e.target.value) : parseInt(e.target.value);
                    const newItem = { ...item, [key]: newValue };
                    isNew ? setNewItemData(newItem) : setEditingItem(newItem);
                  }}
                  required={key === 'field_num' || key === 'amount'}
                />
              ) : (
                <input
                  type="text"
                  id={key}
                  value={value || ''}
                  onChange={(e) => {
                    const newItem = { ...item, [key]: e.target.value || null };
                    isNew ? setNewItemData(newItem) : setEditingItem(newItem);
                  }}
                  required={key === 'short_name' || key === 'fund_name' || key === 'lp_short_name' || 
                           key === 'field' || key === 'activity' || 
                           key === 'entity_from' || key === 'entity_to' || 
                           key === 'related_entity' || key === 'related_fund'}
                />
              )}
            </div>
          );
        })}
        
        <div className="form-actions">
          <button type="submit" className="btn-save">Save</button>
          <button 
            type="button" 
            className="btn-cancel" 
            onClick={() => isNew ? setNewItem(false) : setEditingItem(null)}
          >
            Cancel
          </button>
        </div>
      </form>
    );
  };
  
  // State for the new item data
  const [newItemData, setNewItemData] = useState<DataType>(getNewItemTemplate());
  
  // Reset new item data when tableType changes
  useEffect(() => {
    setNewItemData(getNewItemTemplate());
    setNewItem(false);
    setEditingItem(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tableType]); // We intentionally omit getNewItemTemplate to prevent unnecessary re-renders
  
  // Function to render table headers based on the data
  const renderTableHeaders = () => {
    if (data.length === 0) return null;
    
    const keys = Object.keys(data[0]);
    return (
      <tr>
        {keys.map(key => (
          <th key={key}>{key}</th>
        ))}
        <th>Actions</th>
      </tr>
    );
  };
  
  // Function to render table rows based on the data
  const renderTableRows = () => {
    return data.map((item, index) => {
      const keys = Object.keys(item);
      return (
        <tr key={index}>
          {keys.map(key => (
            <td key={key}>
              {(item as any)[key] !== null ? 
                key.includes('date') ? 
                  new Date((item as any)[key]).toLocaleDateString() : 
                  // Format NaN values to display as empty cells
                  String((item as any)[key]) === "NaN" ? 
                    "" : 
                    String((item as any)[key]) : 
                ''}
            </td>
          ))}
          <td className="action-buttons">
            <button onClick={() => setEditingItem(item)} className="btn-edit">Edit</button>
            <button onClick={() => handleDeleteItem(item)} className="btn-delete">Delete</button>
          </td>
        </tr>
      );
    });
  };
  
  // Function to handle exporting the current table to CSV
  const handleExportTable = async () => {
    setExportStatus('Exporting data...');
    try {
      const response = await fetch(`${API_BASE_URL}/api/data/export/${tableType}`, {
        method: 'POST',
      });
      
      if (!response.ok) {
        throw new Error(`Error exporting data: ${response.statusText}`);
      }
      
      // Removed unused result variable
      await response.json();
      setExportStatus('Export successful!');
      
      // Clear the status message after 3 seconds
      setTimeout(() => {
        setExportStatus(null);
      }, 3000);
    } catch (err) {
      setError(`Failed to export data: ${err instanceof Error ? err.message : String(err)}`);
      setExportStatus(null);
    }
  };
  
  // Function to handle exporting all tables to CSV
  const handleExportAllTables = async () => {
    setExportStatus('Exporting all tables...');
    try {
      const response = await fetch(`${API_BASE_URL}/api/data/export-all`, {
        method: 'POST',
      });
      
      if (!response.ok) {
        throw new Error(`Error exporting all tables: ${response.statusText}`);
      }
      
      // Removed unused result variable
      await response.json();
      setExportStatus('Export successful!');
      
      // Clear the status message after 3 seconds
      setTimeout(() => {
        setExportStatus(null);
      }, 3000);
    } catch (err) {
      setError(`Failed to export all tables: ${err instanceof Error ? err.message : String(err)}`);
      setExportStatus(null);
    }
  };

  return (
    <div className="data-table-component">
      {error && <div className="error-message">{error}</div>}
      {exportStatus && <div className="export-status">{exportStatus}</div>}
      
      <div className="table-actions">
        <h3>{tableType.toUpperCase()} Table</h3>
        <div className="action-buttons-container">
          <button onClick={() => setNewItem(true)} className="btn-add">
            Add New Item
          </button>
          <button onClick={() => fetchData()} className="btn-refresh">
            Refresh Data
          </button>
          <button onClick={handleExportTable} className="btn-export">
            Export Table
          </button>
          <button onClick={handleExportAllTables} className="btn-export-all">
            Export All Tables
          </button>
        </div>
      </div>
      
      {loading ? (
        <div className="loading">Loading data...</div>
      ) : (
        <>
          {newItem && renderForm(newItemData, true)}
          {editingItem && renderForm(editingItem, false)}
          
          {!newItem && !editingItem && (
            data.length > 0 ? (
              <div className="table-responsive">
                <table>
                  <thead>
                    {renderTableHeaders()}
                  </thead>
                  <tbody>
                    {renderTableRows()}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="no-data">No data available</div>
            )
          )}
        </>
      )}
    </div>
  );
};

// Add explicit export type
export type DataTableComponent = React.FC<TableProps>;

export default DataTable;