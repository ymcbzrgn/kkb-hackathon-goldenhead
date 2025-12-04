/**
 * Report Filters
 * Rapor listesi filtreleme
 */

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Filter, X, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import type { ReportStatus } from '@/types';

interface ReportFiltersProps {
  onFilterChange: (filters: FilterState) => void;
  onSearch: (query: string) => void;
}

export interface FilterState {
  status: ReportStatus | 'all';
}

const statusOptions: { value: ReportStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'Tümü' },
  { value: 'pending', label: 'Bekliyor' },
  { value: 'processing', label: 'İşleniyor' },
  { value: 'completed', label: 'Tamamlandı' },
  { value: 'failed', label: 'Hata' },
];

export function ReportFilters({ onFilterChange, onSearch }: ReportFiltersProps) {
  const [filters, setFilters] = useState<FilterState>({ status: 'all' });
  const [searchQuery, setSearchQuery] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  const handleStatusChange = (status: ReportStatus | 'all') => {
    const newFilters = { ...filters, status };
    setFilters(newFilters);
    onFilterChange(newFilters);
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchQuery(value);
    onSearch(value);
  };

  const clearFilters = () => {
    const resetFilters = { status: 'all' as const };
    setFilters(resetFilters);
    setSearchQuery('');
    onFilterChange(resetFilters);
    onSearch('');
  };

  const hasActiveFilters = filters.status !== 'all' || searchQuery.length > 0;

  return (
    <div className="space-y-4">
      {/* Search & Filter Toggle */}
      <div className="flex items-center gap-3">
        {/* Search Input */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <Input
            type="text"
            placeholder="Firma adı ara..."
            value={searchQuery}
            onChange={handleSearchChange}
            className="pl-10"
          />
        </div>

        {/* Filter Toggle */}
        <Button
          variant={showFilters ? 'secondary' : 'ghost'}
          size="sm"
          onClick={() => setShowFilters(!showFilters)}
          className="gap-2"
        >
          <Filter className="w-4 h-4" />
          Filtrele
          {hasActiveFilters && (
            <span className="w-2 h-2 rounded-full bg-accent-500" />
          )}
        </Button>

        {/* Clear Filters */}
        {hasActiveFilters && (
          <Button
            variant="ghost"
            size="sm"
            onClick={clearFilters}
            className="gap-1 text-gray-500 hover:text-red-500"
          >
            <X className="w-4 h-4" />
            Temizle
          </Button>
        )}
      </div>

      {/* Filter Options */}
      {showFilters && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="flex flex-wrap items-center gap-2 p-4 bg-gray-50 rounded-lg"
        >
          <span className="text-sm font-medium text-gray-600 mr-2">Durum:</span>
          {statusOptions.map((option) => (
            <Button
              key={option.value}
              variant={filters.status === option.value ? 'primary' : 'ghost'}
              size="sm"
              onClick={() => handleStatusChange(option.value)}
              className="text-sm"
            >
              {option.label}
            </Button>
          ))}
        </motion.div>
      )}
    </div>
  );
}
