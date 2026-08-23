import React from 'react';

export default function NavigationTabs({ activeTab, onTabChange }) {
  const tabs = [
    { id: 'transcript', label: 'Transcript' },
    { id: 'split', label: 'Split View' },
    { id: 'recap', label: 'AI Recap' },
  ];

  return (
    <div className="nav-tabs">
      {tabs.map((tab) => (
        <div
          key={tab.id}
          className={`tab-item ${activeTab === tab.id ? 'active' : ''}`}
          onClick={() => onTabChange(tab.id)}
        >
          {tab.label}
        </div>
      ))}
    </div>
  );
}
