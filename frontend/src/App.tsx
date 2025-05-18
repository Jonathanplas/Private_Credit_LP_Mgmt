import React, { useState } from 'react';
import LPSelector from './components/LPSelector';
import LPDetails from './components/LPDetails';
import DataManagement from './components/DataManagement';
import './App.css';

const App: React.FC = () => {
  const [selectedLP, setSelectedLP] = useState<string | null>(null);
  const [reportDate, setReportDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [currentView, setCurrentView] = useState<'lp' | 'data'>('lp');

  return (
    <div className="App">
      <header className="App-header">
        <h1>i80 LP Management</h1>
        <nav className="main-navigation">
          <button 
            className={currentView === 'lp' ? 'active' : ''}
            onClick={() => setCurrentView('lp')}
          >
            LP Dashboard
          </button>
          <button 
            className={currentView === 'data' ? 'active' : ''}
            onClick={() => setCurrentView('data')}
          >
            Data Management
          </button>
        </nav>
      </header>
      <main>
        {currentView === 'lp' ? (
          <>
            <LPSelector 
              onLPSelect={(lp: string) => setSelectedLP(lp)} 
              onDateChange={(date: string) => setReportDate(date)}
            />
            {selectedLP && <LPDetails lpShortName={selectedLP} reportDate={reportDate} />}
          </>
        ) : (
          <DataManagement />
        )}
      </main>
    </div>
  );
};

export default App;