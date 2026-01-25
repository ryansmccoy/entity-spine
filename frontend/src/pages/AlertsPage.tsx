import { useState } from 'react';
import {
  Bell,
  Plus,
  Edit2,
  Trash2,
  Power,
  PowerOff,
  Filter,
  Clock,
  AlertTriangle,
  Search,
  Mail,
  Webhook,
  ChevronDown,
  ChevronUp,
  X,
} from 'lucide-react';

// Alert condition types
interface AlertCondition {
  type: 'keywords' | 'form_types' | 'filers' | 'cik' | 'industry';
  operator: 'contains' | 'equals' | 'not_contains' | 'regex';
  value: string | string[];
}

interface AlertAction {
  type: 'notification' | 'email' | 'webhook';
  enabled: boolean;
  config?: {
    email?: string;
    webhook_url?: string;
    include_content?: boolean;
  };
}

interface Alert {
  alert_id: string;
  name: string;
  description?: string;
  enabled: boolean;
  conditions: AlertCondition[];
  actions: AlertAction[];
  feed_ids?: string[];
  triggered_count: number;
  last_triggered_at?: string;
  created_at: string;
  updated_at: string;
}

// Sample data - will be replaced with API calls
const sampleAlerts: Alert[] = [
  {
    alert_id: '1',
    name: '10-K Annual Reports',
    description: 'Get notified when companies file annual reports',
    enabled: true,
    conditions: [
      { type: 'form_types', operator: 'contains', value: ['10-K', '10-K/A'] },
    ],
    actions: [
      { type: 'notification', enabled: true },
      { type: 'email', enabled: true, config: { email: 'user@example.com' } },
    ],
    triggered_count: 45,
    last_triggered_at: '2025-01-15T10:30:00Z',
    created_at: '2024-12-01T00:00:00Z',
    updated_at: '2025-01-15T10:30:00Z',
  },
  {
    alert_id: '2',
    name: 'Apple & Microsoft Filings',
    description: 'Track all filings from AAPL and MSFT',
    enabled: true,
    conditions: [
      { type: 'cik', operator: 'equals', value: ['0000320193', '0000789019'] },
    ],
    actions: [
      { type: 'notification', enabled: true },
    ],
    triggered_count: 12,
    last_triggered_at: '2025-01-10T14:22:00Z',
    created_at: '2024-11-15T00:00:00Z',
    updated_at: '2025-01-10T14:22:00Z',
  },
  {
    alert_id: '3',
    name: 'Insider Trading',
    description: 'Alert on Form 4 insider trading disclosures',
    enabled: false,
    conditions: [
      { type: 'form_types', operator: 'equals', value: ['4'] },
      { type: 'keywords', operator: 'contains', value: 'acquisition' },
    ],
    actions: [
      { type: 'notification', enabled: true },
      { type: 'webhook', enabled: true, config: { webhook_url: 'https://hooks.slack.com/...' } },
    ],
    triggered_count: 234,
    last_triggered_at: '2024-12-20T08:15:00Z',
    created_at: '2024-06-01T00:00:00Z',
    updated_at: '2024-12-20T08:15:00Z',
  },
];

// Alert Editor Modal Component
interface AlertEditorProps {
  alert?: Alert;
  onSave: (alert: Partial<Alert>) => void;
  onCancel: () => void;
}

function AlertEditor({ alert, onSave, onCancel }: AlertEditorProps) {
  const [name, setName] = useState(alert?.name || '');
  const [description, setDescription] = useState(alert?.description || '');
  const [conditions, setConditions] = useState<AlertCondition[]>(
    alert?.conditions || [{ type: 'keywords', operator: 'contains', value: '' }]
  );
  const [actions, setActions] = useState<AlertAction[]>(
    alert?.actions || [{ type: 'notification', enabled: true }]
  );

  const addCondition = () => {
    setConditions([...conditions, { type: 'keywords', operator: 'contains', value: '' }]);
  };

  const removeCondition = (index: number) => {
    setConditions(conditions.filter((_, i) => i !== index));
  };

  const updateCondition = (index: number, updates: Partial<AlertCondition>) => {
    setConditions(conditions.map((c, i) => i === index ? { ...c, ...updates } : c));
  };

  const toggleAction = (type: AlertAction['type']) => {
    const existing = actions.find(a => a.type === type);
    if (existing) {
      setActions(actions.map(a => a.type === type ? { ...a, enabled: !a.enabled } : a));
    } else {
      setActions([...actions, { type, enabled: true }]);
    }
  };

  const handleSave = () => {
    onSave({
      name,
      description,
      conditions,
      actions,
    });
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            {alert ? 'Edit Alert' : 'Create Alert'}
          </h2>
          <button onClick={onCancel} className="text-gray-500 hover:text-gray-700">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-4 space-y-6">
          {/* Basic Info */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Alert Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Tech Company 10-K Filings"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Description (optional)
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe what this alert monitors..."
                rows={2}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>

          {/* Conditions */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Conditions (ALL must match)
              </label>
              <button
                onClick={addCondition}
                className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1"
              >
                <Plus className="w-4 h-4" />
                Add Condition
              </button>
            </div>
            <div className="space-y-3">
              {conditions.map((condition, index) => (
                <div key={index} className="flex items-center gap-2 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                  <select
                    value={condition.type}
                    onChange={(e) => updateCondition(index, { type: e.target.value as AlertCondition['type'] })}
                    className="px-2 py-1.5 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-sm"
                  >
                    <option value="keywords">Keywords</option>
                    <option value="form_types">Form Type</option>
                    <option value="filers">Filer Name</option>
                    <option value="cik">CIK</option>
                    <option value="industry">Industry</option>
                  </select>
                  <select
                    value={condition.operator}
                    onChange={(e) => updateCondition(index, { operator: e.target.value as AlertCondition['operator'] })}
                    className="px-2 py-1.5 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-sm"
                  >
                    <option value="contains">contains</option>
                    <option value="equals">equals</option>
                    <option value="not_contains">does not contain</option>
                    <option value="regex">matches regex</option>
                  </select>
                  <input
                    type="text"
                    value={Array.isArray(condition.value) ? condition.value.join(', ') : condition.value}
                    onChange={(e) => updateCondition(index, { value: e.target.value })}
                    placeholder="Value (comma-separated for multiple)"
                    className="flex-1 px-2 py-1.5 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-sm"
                  />
                  {conditions.length > 1 && (
                    <button
                      onClick={() => removeCondition(index)}
                      className="p-1 text-gray-400 hover:text-red-500"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
              Actions
            </label>
            <div className="space-y-2">
              <label className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg cursor-pointer">
                <input
                  type="checkbox"
                  checked={actions.some(a => a.type === 'notification' && a.enabled)}
                  onChange={() => toggleAction('notification')}
                  className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <Bell className="w-5 h-5 text-gray-500" />
                <span className="text-sm text-gray-700 dark:text-gray-300">In-app notification</span>
              </label>
              <label className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg cursor-pointer">
                <input
                  type="checkbox"
                  checked={actions.some(a => a.type === 'email' && a.enabled)}
                  onChange={() => toggleAction('email')}
                  className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <Mail className="w-5 h-5 text-gray-500" />
                <span className="text-sm text-gray-700 dark:text-gray-300">Email notification</span>
              </label>
              <label className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg cursor-pointer">
                <input
                  type="checkbox"
                  checked={actions.some(a => a.type === 'webhook' && a.enabled)}
                  onChange={() => toggleAction('webhook')}
                  className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <Webhook className="w-5 h-5 text-gray-500" />
                <span className="text-sm text-gray-700 dark:text-gray-300">Webhook (Slack, Discord, etc.)</span>
              </label>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 p-4 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!name.trim()}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {alert ? 'Save Changes' : 'Create Alert'}
          </button>
        </div>
      </div>
    </div>
  );
}

// Main AlertsPage Component
export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>(sampleAlerts);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterEnabled, setFilterEnabled] = useState<boolean | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [editingAlert, setEditingAlert] = useState<Alert | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  // Filter alerts
  const filteredAlerts = alerts.filter(alert => {
    const matchesSearch = searchQuery === '' ||
      alert.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      alert.description?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesEnabled = filterEnabled === null || alert.enabled === filterEnabled;
    return matchesSearch && matchesEnabled;
  });

  const toggleAlertEnabled = (alertId: string) => {
    setAlerts(alerts.map(a => 
      a.alert_id === alertId ? { ...a, enabled: !a.enabled } : a
    ));
  };

  const deleteAlert = (alertId: string) => {
    if (confirm('Are you sure you want to delete this alert?')) {
      setAlerts(alerts.filter(a => a.alert_id !== alertId));
    }
  };

  const handleSaveAlert = (alertData: Partial<Alert>) => {
    if (editingAlert) {
      // Update existing
      setAlerts(alerts.map(a =>
        a.alert_id === editingAlert.alert_id
          ? { ...a, ...alertData, updated_at: new Date().toISOString() }
          : a
      ));
    } else {
      // Create new
      const newAlert: Alert = {
        alert_id: crypto.randomUUID(),
        name: alertData.name || 'New Alert',
        description: alertData.description,
        enabled: true,
        conditions: alertData.conditions || [],
        actions: alertData.actions || [{ type: 'notification', enabled: true }],
        triggered_count: 0,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      setAlerts([newAlert, ...alerts]);
    }
    setEditingAlert(null);
    setIsCreating(false);
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return 'Never';
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getConditionLabel = (condition: AlertCondition) => {
    const typeLabels: Record<AlertCondition['type'], string> = {
      keywords: 'Keywords',
      form_types: 'Form Type',
      filers: 'Filer',
      cik: 'CIK',
      industry: 'Industry',
    };
    const value = Array.isArray(condition.value) ? condition.value.join(', ') : condition.value;
    return `${typeLabels[condition.type]} ${condition.operator} "${value}"`;
  };

  const getActionIcons = (actions: AlertAction[]) => {
    return actions.filter(a => a.enabled).map(action => {
      switch (action.type) {
        case 'notification':
          return <span key="notification" title="In-app notification"><Bell className="w-4 h-4" /></span>;
        case 'email':
          return <span key="email" title="Email notification"><Mail className="w-4 h-4" /></span>;
        case 'webhook':
          return <span key="webhook" title="Webhook"><Webhook className="w-4 h-4" /></span>;
      }
    });
  };

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <AlertTriangle className="w-7 h-7 text-yellow-500" />
                Alerts
              </h1>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                Get notified when new filings match your criteria
              </p>
            </div>
            <button
              onClick={() => setIsCreating(true)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Plus className="w-5 h-5" />
              Create Alert
            </button>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="flex items-center gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search alerts..."
              className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div className="flex items-center gap-2">
            <Filter className="w-5 h-5 text-gray-400" />
            <select
              value={filterEnabled === null ? 'all' : filterEnabled ? 'enabled' : 'disabled'}
              onChange={(e) => {
                const val = e.target.value;
                setFilterEnabled(val === 'all' ? null : val === 'enabled');
              }}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-sm"
            >
              <option value="all">All Alerts</option>
              <option value="enabled">Enabled Only</option>
              <option value="disabled">Disabled Only</option>
            </select>
          </div>
        </div>
      </div>

      {/* Alerts List */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-8">
        {filteredAlerts.length === 0 ? (
          <div className="bg-white dark:bg-gray-800 rounded-lg p-12 text-center">
            <AlertTriangle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              No alerts found
            </h3>
            <p className="text-gray-500 dark:text-gray-400 mb-4">
              {searchQuery ? 'Try adjusting your search criteria' : 'Create your first alert to get started'}
            </p>
            {!searchQuery && (
              <button
                onClick={() => setIsCreating(true)}
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                <Plus className="w-5 h-5" />
                Create Alert
              </button>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {filteredAlerts.map((alert) => (
              <div
                key={alert.alert_id}
                className={`bg-white dark:bg-gray-800 rounded-lg border ${
                  alert.enabled
                    ? 'border-gray-200 dark:border-gray-700'
                    : 'border-gray-200 dark:border-gray-700 opacity-60'
                }`}
              >
                {/* Alert Header */}
                <div
                  className="flex items-center gap-4 p-4 cursor-pointer"
                  onClick={() => setExpandedId(expandedId === alert.alert_id ? null : alert.alert_id)}
                >
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleAlertEnabled(alert.alert_id);
                    }}
                    className={`p-2 rounded-lg transition-colors ${
                      alert.enabled
                        ? 'bg-green-100 text-green-600 hover:bg-green-200'
                        : 'bg-gray-100 text-gray-400 hover:bg-gray-200'
                    }`}
                    title={alert.enabled ? 'Disable alert' : 'Enable alert'}
                  >
                    {alert.enabled ? <Power className="w-5 h-5" /> : <PowerOff className="w-5 h-5" />}
                  </button>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="text-base font-medium text-gray-900 dark:text-white truncate">
                        {alert.name}
                      </h3>
                      <div className="flex items-center gap-1 text-gray-400">
                        {getActionIcons(alert.actions)}
                      </div>
                    </div>
                    {alert.description && (
                      <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
                        {alert.description}
                      </p>
                    )}
                  </div>

                  <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
                    <div className="flex items-center gap-1">
                      <Bell className="w-4 h-4" />
                      <span>{alert.triggered_count}</span>
                    </div>
                    <div className="flex items-center gap-1" title={`Last triggered: ${formatDate(alert.last_triggered_at)}`}>
                      <Clock className="w-4 h-4" />
                      <span className="whitespace-nowrap">
                        {alert.last_triggered_at ? formatDate(alert.last_triggered_at).split(',')[0] : 'Never'}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditingAlert(alert);
                      }}
                      className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg"
                      title="Edit alert"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteAlert(alert.alert_id);
                      }}
                      className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg"
                      title="Delete alert"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                    {expandedId === alert.alert_id ? (
                      <ChevronUp className="w-5 h-5 text-gray-400" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-gray-400" />
                    )}
                  </div>
                </div>

                {/* Expanded Details */}
                {expandedId === alert.alert_id && (
                  <div className="border-t border-gray-200 dark:border-gray-700 p-4 bg-gray-50 dark:bg-gray-800/50">
                    <div className="grid grid-cols-2 gap-6">
                      <div>
                        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                          Conditions
                        </h4>
                        <div className="space-y-1">
                          {alert.conditions.map((condition, i) => (
                            <div
                              key={i}
                              className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400"
                            >
                              <Filter className="w-4 h-4 text-gray-400" />
                              <span>{getConditionLabel(condition)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                      <div>
                        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                          Actions
                        </h4>
                        <div className="space-y-1">
                          {alert.actions.filter(a => a.enabled).map((action, i) => (
                            <div
                              key={i}
                              className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400"
                            >
                              {action.type === 'notification' && (
                                <>
                                  <Bell className="w-4 h-4 text-gray-400" />
                                  <span>In-app notification</span>
                                </>
                              )}
                              {action.type === 'email' && (
                                <>
                                  <Mail className="w-4 h-4 text-gray-400" />
                                  <span>Email to {action.config?.email || 'configured address'}</span>
                                </>
                              )}
                              {action.type === 'webhook' && (
                                <>
                                  <Webhook className="w-4 h-4 text-gray-400" />
                                  <span>Webhook</span>
                                </>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                    <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
                      <span>Created: {formatDate(alert.created_at)}</span>
                      <span>•</span>
                      <span>Updated: {formatDate(alert.updated_at)}</span>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Alert Editor Modal */}
      {(isCreating || editingAlert) && (
        <AlertEditor
          alert={editingAlert || undefined}
          onSave={handleSaveAlert}
          onCancel={() => {
            setIsCreating(false);
            setEditingAlert(null);
          }}
        />
      )}
    </div>
  );
}
