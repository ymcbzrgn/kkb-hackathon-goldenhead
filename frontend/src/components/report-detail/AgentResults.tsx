/**
 * AgentResults Component
 * 3 agent sonucunu tab yapısında gösteren container
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  FileText, 
  Gavel, 
  Newspaper, 
  CheckCircle2, 
  XCircle, 
  Loader2,
  Clock
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { TsgResults } from './TsgResults';
import { IhaleResults } from './IhaleResults';
import { NewsResults } from './NewsResults';
import type { AgentResults as AgentResultsType } from '@/types';

interface AgentResultsProps {
  results: AgentResultsType;
}

type TabId = 'tsg' | 'ihale' | 'news';

const tabs: { id: TabId; label: string; icon: typeof FileText }[] = [
  { id: 'tsg', label: 'Ticaret Sicil', icon: FileText },
  { id: 'ihale', label: 'İhale Yasaklılık', icon: Gavel },
  { id: 'news', label: 'Medya Taraması', icon: Newspaper },
];

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'completed':
      return <CheckCircle2 className="w-4 h-4 text-green-500" />;
    case 'failed':
      return <XCircle className="w-4 h-4 text-red-500" />;
    case 'running':
      return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
    default:
      return <Clock className="w-4 h-4 text-gray-400" />;
  }
}

export function AgentResults({ results }: AgentResultsProps) {
  const [activeTab, setActiveTab] = useState<TabId>('tsg');

  const getStatus = (tabId: TabId) => {
    return results[tabId].status;
  };

  const getDuration = (tabId: TabId) => {
    const duration = results[tabId].duration_seconds;
    if (!duration) return null;
    return `${duration.toFixed(1)}s`;
  };

  return (
    <Card className="overflow-hidden">
      {/* Tab Headers */}
      <div className="flex border-b bg-gray-50">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          const status = getStatus(tab.id);
          const duration = getDuration(tab.id);
          const Icon = tab.icon;

          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium transition-colors relative ${
                isActive
                  ? 'text-kkb-700 bg-white'
                  : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span className="hidden sm:inline">{tab.label}</span>
              <StatusIcon status={status} />
              {duration && (
                <span className="text-xs text-gray-400 hidden md:inline">
                  ({duration})
                </span>
              )}
              {isActive && (
                <motion.div
                  layoutId="activeTab"
                  className="absolute bottom-0 left-0 right-0 h-0.5 bg-kkb-600"
                />
              )}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      <div className="p-6">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            {activeTab === 'tsg' && (
              results.tsg.status === 'completed' && results.tsg.data ? (
                <TsgResults data={results.tsg.data} />
              ) : (
                <EmptyAgentState status={results.tsg.status} agentName="TSG" />
              )
            )}
            {activeTab === 'ihale' && (
              results.ihale.status === 'completed' && results.ihale.data ? (
                <IhaleResults data={results.ihale.data} />
              ) : (
                <EmptyAgentState status={results.ihale.status} agentName="İhale" />
              )
            )}
            {activeTab === 'news' && (
              results.news.status === 'completed' && results.news.data ? (
                <NewsResults data={results.news.data} />
              ) : (
                <EmptyAgentState status={results.news.status} agentName="Haber" />
              )
            )}
          </motion.div>
        </AnimatePresence>
      </div>
    </Card>
  );
}

function EmptyAgentState({ status, agentName }: { status: string; agentName: string }) {
  if (status === 'running') {
    return (
      <div className="text-center py-12">
        <Loader2 className="w-12 h-12 text-kkb-500 animate-spin mx-auto mb-4" />
        <h4 className="font-semibold text-gray-800 mb-1">{agentName} Agent Çalışıyor</h4>
        <p className="text-sm text-gray-500">Veriler toplanıyor, lütfen bekleyin...</p>
      </div>
    );
  }

  if (status === 'failed') {
    return (
      <div className="text-center py-12">
        <XCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
        <h4 className="font-semibold text-gray-800 mb-1">{agentName} Agent Başarısız</h4>
        <p className="text-sm text-gray-500">Veri toplama sırasında bir hata oluştu.</p>
      </div>
    );
  }

  return (
    <div className="text-center py-12">
      <Clock className="w-12 h-12 text-gray-400 mx-auto mb-4" />
      <h4 className="font-semibold text-gray-800 mb-1">{agentName} Agent Bekliyor</h4>
      <p className="text-sm text-gray-500">Henüz veri yok.</p>
    </div>
  );
}
