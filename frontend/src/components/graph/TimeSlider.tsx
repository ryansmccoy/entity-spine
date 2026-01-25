/**
 * Time Slider Component
 * 
 * Allows temporal navigation through relationship data.
 * Shows when relationships were valid and enables "time travel"
 * to see the graph at any point in history.
 */

import { useState, useEffect, useCallback, useMemo } from 'react';

interface TimeSliderProps {
  minDate: Date;
  maxDate: Date;
  currentDate: Date;
  onChange: (date: Date) => void;
  isPlaying?: boolean;
  onPlayToggle?: () => void;
  playSpeed?: number; // months per second
}

export function TimeSlider({
  minDate,
  maxDate,
  currentDate,
  onChange,
  isPlaying = false,
  onPlayToggle,
  playSpeed = 3, // 3 months per second by default
}: TimeSliderProps) {
  const [isDragging, setIsDragging] = useState(false);

  // Calculate slider position (0-100)
  const position = useMemo(() => {
    const total = maxDate.getTime() - minDate.getTime();
    const current = currentDate.getTime() - minDate.getTime();
    return Math.min(100, Math.max(0, (current / total) * 100));
  }, [minDate, maxDate, currentDate]);

  // Handle slider change
  const handleSliderChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const percent = Number(e.target.value);
    const total = maxDate.getTime() - minDate.getTime();
    const newTime = minDate.getTime() + (total * percent / 100);
    onChange(new Date(newTime));
  }, [minDate, maxDate, onChange]);

  // Auto-play animation
  useEffect(() => {
    if (!isPlaying) return;

    const interval = setInterval(() => {
      const monthsToAdd = playSpeed / 10; // Divided by 10 since interval is 100ms
      const newDate = new Date(currentDate);
      newDate.setMonth(newDate.getMonth() + monthsToAdd);

      if (newDate >= maxDate) {
        onChange(minDate); // Loop back to start
      } else {
        onChange(newDate);
      }
    }, 100);

    return () => clearInterval(interval);
  }, [isPlaying, currentDate, minDate, maxDate, onChange, playSpeed]);

  // Format date for display
  const formatDate = (date: Date): string => {
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
    });
  };

  // Key events/milestones for markers
  const milestones = useMemo(() => {
    const events = [
      { date: new Date('2016-09-01'), label: 'SoftBank acquires ARM' },
      { date: new Date('2019-07-01'), label: 'Microsoft invests in OpenAI' },
      { date: new Date('2022-01-01'), label: 'Chip shortage peak' },
      { date: new Date('2023-01-01'), label: 'ChatGPT launch' },
      { date: new Date('2024-01-01'), label: 'AI chip boom' },
    ];

    return events.filter(e => e.date >= minDate && e.date <= maxDate).map(e => ({
      ...e,
      position: ((e.date.getTime() - minDate.getTime()) / (maxDate.getTime() - minDate.getTime())) * 100,
    }));
  }, [minDate, maxDate]);

  return (
    <div className="bg-gray-800/95 border-t border-gray-700 p-3">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-400">⏱️ Timeline</span>
          {onPlayToggle && (
            <button
              onClick={onPlayToggle}
              className={`px-2 py-1 rounded text-xs ${
                isPlaying
                  ? 'bg-red-600 hover:bg-red-700'
                  : 'bg-blue-600 hover:bg-blue-700'
              }`}
            >
              {isPlaying ? '⏸ Pause' : '▶ Play'}
            </button>
          )}
        </div>
        <div className="text-sm font-medium text-blue-400">
          {formatDate(currentDate)}
        </div>
      </div>

      {/* Slider container */}
      <div className="relative">
        {/* Milestone markers */}
        <div className="absolute inset-x-0 top-0 h-full pointer-events-none">
          {milestones.map((m, i) => (
            <div
              key={i}
              className="absolute top-1/2 -translate-y-1/2 group"
              style={{ left: `${m.position}%` }}
            >
              <div className="w-1 h-4 bg-yellow-500/60 rounded" />
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity">
                <div className="bg-gray-900 text-xs px-2 py-1 rounded shadow-lg">
                  {m.label}
                  <br />
                  <span className="text-gray-400">{formatDate(m.date)}</span>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Range slider */}
        <input
          type="range"
          min={0}
          max={100}
          step={0.1}
          value={position}
          onChange={handleSliderChange}
          onMouseDown={() => setIsDragging(true)}
          onMouseUp={() => setIsDragging(false)}
          className={`w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer
            [&::-webkit-slider-thumb]:appearance-none
            [&::-webkit-slider-thumb]:w-4
            [&::-webkit-slider-thumb]:h-4
            [&::-webkit-slider-thumb]:rounded-full
            [&::-webkit-slider-thumb]:bg-blue-500
            [&::-webkit-slider-thumb]:cursor-pointer
            [&::-webkit-slider-thumb]:transition-all
            ${isDragging ? '[&::-webkit-slider-thumb]:scale-125 [&::-webkit-slider-thumb]:bg-blue-400' : ''}
            [&::-webkit-slider-thumb]:hover:scale-110
          `}
          style={{
            background: `linear-gradient(to right, #3b82f6 0%, #3b82f6 ${position}%, #374151 ${position}%, #374151 100%)`,
          }}
        />

        {/* Date labels */}
        <div className="flex justify-between mt-1 text-xs text-gray-500">
          <span>{formatDate(minDate)}</span>
          <span>{formatDate(maxDate)}</span>
        </div>
      </div>

      {/* Quick jump buttons */}
      <div className="flex gap-2 mt-2">
        {[2020, 2022, 2024, 2025, 2026].map(year => (
          <button
            key={year}
            onClick={() => onChange(new Date(`${year}-01-01`))}
            className={`px-2 py-0.5 text-xs rounded ${
              currentDate.getFullYear() === year
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
            }`}
          >
            {year}
          </button>
        ))}
      </div>
    </div>
  );
}

export default TimeSlider;
