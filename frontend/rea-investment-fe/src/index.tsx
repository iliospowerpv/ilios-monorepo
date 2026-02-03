import React from 'react';
import ReactDOM from 'react-dom/client';
import { LicenseManager } from 'ag-grid-enterprise';
import './index.css';
import './styles/focus-highlight.css';
import App from './App';

if (typeof process.env.REACT_APP_AG_GRID_LICENSE_KEY === 'string') {
  LicenseManager.setLicenseKey(process.env.REACT_APP_AG_GRID_LICENSE_KEY);
}

const root = ReactDOM.createRoot(document.getElementById('root') as HTMLElement);
root.render(<App />);
