import { useState } from 'react';
import {
  Shield,
  Smartphone,
  Mail,
  ChevronRight,
  AlertTriangle,
  Copy,
  CheckCircle,
  XCircle,
  ArrowLeft,
  Eye,
  EyeOff,
  Download,
  Printer,
  QrCode,
} from 'lucide-react';
import { clsx } from 'clsx';

// Types
interface MFAMethod {
  id: 'totp' | 'sms' | 'email';
  name: string;
  description: string;
  icon: React.ElementType;
  recommended?: boolean;
}

interface MFASetupState {
  step: 'select-method' | 'setup-totp' | 'verify' | 'backup-codes' | 'complete';
  selectedMethod?: MFAMethod['id'];
  totpSecret?: string;
  totpUri?: string;
  qrCodeUrl?: string;
  backupCodes?: string[];
}

interface MFASetupModalProps {
  isOpen: boolean;
  onClose: () => void;
  onComplete: () => void;
  userEmail: string;
  userPhone?: string;
  onRequestTOTPSetup: () => Promise<{ secret: string; uri: string; qrCodeUrl: string }>;
  onVerifyCode: (code: string, method: MFAMethod['id']) => Promise<{ success: boolean; backupCodes?: string[] }>;
  onSendEmailCode: () => Promise<void>;
  onSendSMSCode: () => Promise<void>;
}

const MFA_METHODS: MFAMethod[] = [
  {
    id: 'totp',
    name: 'Authenticator App',
    description: 'Use an app like Google Authenticator or Authy to generate codes',
    icon: Smartphone,
    recommended: true,
  },
  {
    id: 'email',
    name: 'Email',
    description: 'Receive codes via email',
    icon: Mail,
  },
  {
    id: 'sms',
    name: 'SMS',
    description: 'Receive codes via text message',
    icon: Smartphone,
  },
];

// Code input component
function CodeInput({
  length = 6,
  value,
  onChange,
  error,
  autoFocus = true,
}: {
  length?: number;
  value: string;
  onChange: (value: string) => void;
  error?: string;
  autoFocus?: boolean;
}) {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>, index: number) => {
    const char = e.target.value.slice(-1);
    if (!/^\d*$/.test(char)) return;

    const newValue = value.split('');
    newValue[index] = char;
    const result = newValue.join('').slice(0, length);
    onChange(result);

    // Auto-focus next input
    if (char && index < length - 1) {
      const next = e.target.nextElementSibling as HTMLInputElement;
      next?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>, index: number) => {
    if (e.key === 'Backspace' && !value[index] && index > 0) {
      const prev = (e.target as HTMLElement).previousElementSibling as HTMLInputElement;
      prev?.focus();
    }
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, length);
    onChange(pasted);
  };

  return (
    <div>
      <div className="flex justify-center gap-2">
        {Array.from({ length }).map((_, i) => (
          <input
            key={i}
            type="text"
            inputMode="numeric"
            maxLength={1}
            value={value[i] || ''}
            onChange={(e) => handleChange(e, i)}
            onKeyDown={(e) => handleKeyDown(e, i)}
            onPaste={handlePaste}
            autoFocus={autoFocus && i === 0}
            className={clsx(
              'w-12 h-14 text-center text-2xl font-mono border rounded-lg focus:outline-none focus:ring-2 transition-colors',
              error
                ? 'border-red-300 focus:ring-red-500 bg-red-50 dark:bg-red-900/20 dark:border-red-700'
                : 'border-gray-300 dark:border-gray-600 focus:ring-primary-500 bg-white dark:bg-gray-800'
            )}
          />
        ))}
      </div>
      {error && (
        <p className="text-center text-sm text-red-600 dark:text-red-400 mt-2 flex items-center justify-center gap-1">
          <XCircle className="h-4 w-4" />
          {error}
        </p>
      )}
    </div>
  );
}

// Backup codes display
function BackupCodesDisplay({
  codes,
  onCopy,
  onDownload,
  onPrint,
}: {
  codes: string[];
  onCopy: () => void;
  onDownload: () => void;
  onPrint: () => void;
}) {
  return (
    <div className="space-y-4">
      <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-yellow-600 dark:text-yellow-500 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-yellow-800 dark:text-yellow-200">
            <p className="font-medium">Save these backup codes in a secure place</p>
            <p className="mt-1">
              Each code can only be used once. If you lose access to your authenticator app, you can use these codes to sign in.
            </p>
          </div>
        </div>
      </div>

      <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 font-mono text-sm">
        <div className="grid grid-cols-2 gap-2">
          {codes.map((code, i) => (
            <div key={i} className="text-gray-700 dark:text-gray-300 py-1 px-2 bg-white dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700">
              {code}
            </div>
          ))}
        </div>
      </div>

      <div className="flex items-center justify-center gap-2">
        <button
          onClick={onCopy}
          className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
        >
          <Copy className="h-4 w-4" />
          Copy
        </button>
        <button
          onClick={onDownload}
          className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
        >
          <Download className="h-4 w-4" />
          Download
        </button>
        <button
          onClick={onPrint}
          className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
        >
          <Printer className="h-4 w-4" />
          Print
        </button>
      </div>
    </div>
  );
}

// Main component
export function MFASetupModal({
  isOpen,
  onClose,
  onComplete,
  userEmail,
  userPhone,
  onRequestTOTPSetup,
  onVerifyCode,
  onSendEmailCode,
  onSendSMSCode,
}: MFASetupModalProps) {
  const [state, setState] = useState<MFASetupState>({ step: 'select-method' });
  const [code, setCode] = useState('');
  const [error, setError] = useState<string>();
  const [isLoading, setIsLoading] = useState(false);
  const [showSecret, setShowSecret] = useState(false);

  if (!isOpen) return null;

  const handleSelectMethod = async (method: MFAMethod['id']) => {
    setIsLoading(true);
    setError(undefined);

    try {
      if (method === 'totp') {
        const { secret, uri, qrCodeUrl } = await onRequestTOTPSetup();
        setState({
          step: 'setup-totp',
          selectedMethod: method,
          totpSecret: secret,
          totpUri: uri,
          qrCodeUrl,
        });
      } else if (method === 'email') {
        await onSendEmailCode();
        setState({ step: 'verify', selectedMethod: method });
      } else if (method === 'sms') {
        await onSendSMSCode();
        setState({ step: 'verify', selectedMethod: method });
      }
    } catch (err) {
      setError('Failed to start setup. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerify = async () => {
    if (code.length < 6) return;

    setIsLoading(true);
    setError(undefined);

    try {
      const result = await onVerifyCode(code, state.selectedMethod!);
      if (result.success) {
        if (result.backupCodes) {
          setState({ ...state, step: 'backup-codes', backupCodes: result.backupCodes });
        } else {
          setState({ ...state, step: 'complete' });
        }
      } else {
        setError('Invalid code. Please try again.');
        setCode('');
      }
    } catch (err) {
      setError('Verification failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopyBackupCodes = () => {
    if (state.backupCodes) {
      navigator.clipboard.writeText(state.backupCodes.join('\n'));
    }
  };

  const handleDownloadBackupCodes = () => {
    if (state.backupCodes) {
      const content = `SEC Edgar Backup Codes\n\nGenerated: ${new Date().toISOString()}\n\n${state.backupCodes.join('\n')}\n\nEach code can only be used once.`;
      const blob = new Blob([content], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'backup-codes.txt';
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  const handlePrintBackupCodes = () => {
    if (state.backupCodes) {
      const content = `
        <html>
          <head><title>Backup Codes</title></head>
          <body style="font-family: monospace; padding: 20px;">
            <h2>SEC Edgar Backup Codes</h2>
            <p>Generated: ${new Date().toLocaleDateString()}</p>
            <ul style="list-style: none; padding: 0;">
              ${state.backupCodes.map(c => `<li style="padding: 4px 0;">${c}</li>`).join('')}
            </ul>
            <p style="color: #666; margin-top: 20px;">Each code can only be used once.</p>
          </body>
        </html>
      `;
      const printWindow = window.open('', '_blank');
      printWindow?.document.write(content);
      printWindow?.document.close();
      printWindow?.print();
    }
  };

  const copySecret = () => {
    if (state.totpSecret) {
      navigator.clipboard.writeText(state.totpSecret);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-xl max-w-md w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2">
            {state.step !== 'select-method' && state.step !== 'complete' && (
              <button
                onClick={() => setState({ step: 'select-method' })}
                className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
              >
                <ArrowLeft className="h-5 w-5 text-gray-500" />
              </button>
            )}
            <Shield className="h-5 w-5 text-primary-500" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              {state.step === 'complete' ? 'Two-Factor Authentication Enabled' : 'Enable Two-Factor Authentication'}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
          >
            <XCircle className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {/* Step 1: Select Method */}
          {state.step === 'select-method' && (
            <div className="space-y-4">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Add an extra layer of security to your account by requiring a verification code in addition to your password.
              </p>
              
              <div className="space-y-2">
                {MFA_METHODS.map((method) => (
                  <button
                    key={method.id}
                    onClick={() => handleSelectMethod(method.id)}
                    disabled={isLoading || (method.id === 'sms' && !userPhone)}
                    className={clsx(
                      'w-full flex items-center gap-4 p-4 rounded-lg border transition-colors text-left',
                      'hover:border-primary-300 hover:bg-primary-50 dark:hover:border-primary-700 dark:hover:bg-primary-900/20',
                      method.id === 'sms' && !userPhone
                        ? 'opacity-50 cursor-not-allowed'
                        : 'border-gray-200 dark:border-gray-700'
                    )}
                  >
                    <div className="p-3 bg-gray-100 dark:bg-gray-800 rounded-lg">
                      <method.icon className="h-6 w-6 text-gray-600 dark:text-gray-400" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-gray-900 dark:text-white">{method.name}</span>
                        {method.recommended && (
                          <span className="text-xs bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 px-2 py-0.5 rounded">
                            Recommended
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                        {method.description}
                        {method.id === 'sms' && !userPhone && ' (Add phone number first)'}
                      </p>
                    </div>
                    <ChevronRight className="h-5 w-5 text-gray-400" />
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Step 2: TOTP Setup */}
          {state.step === 'setup-totp' && (
            <div className="space-y-6">
              <div className="text-center">
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                  Scan this QR code with your authenticator app (Google Authenticator, Authy, etc.)
                </p>
                
                {state.qrCodeUrl ? (
                  <div className="inline-block p-4 bg-white rounded-lg shadow-sm">
                    <img
                      src={state.qrCodeUrl}
                      alt="QR Code"
                      className="w-48 h-48"
                    />
                  </div>
                ) : (
                  <div className="inline-flex items-center justify-center w-56 h-56 bg-gray-100 dark:bg-gray-800 rounded-lg">
                    <QrCode className="h-12 w-12 text-gray-400" />
                  </div>
                )}
              </div>

              <div className="text-center">
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                  Or enter this code manually:
                </p>
                <div className="relative inline-flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-800 rounded-lg font-mono text-sm">
                  {showSecret ? state.totpSecret : '••••••••••••••••'}
                  <button
                    onClick={() => setShowSecret(!showSecret)}
                    className="text-gray-500 hover:text-gray-700"
                  >
                    {showSecret ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                  <button
                    onClick={copySecret}
                    className="text-gray-500 hover:text-gray-700"
                  >
                    <Copy className="h-4 w-4" />
                  </button>
                </div>
              </div>

              <button
                onClick={() => setState({ ...state, step: 'verify' })}
                className="w-full py-2 px-4 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg"
              >
                Continue
              </button>
            </div>
          )}

          {/* Step 3: Verify */}
          {state.step === 'verify' && (
            <div className="space-y-6">
              <div className="text-center">
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
                  {state.selectedMethod === 'totp'
                    ? 'Enter the 6-digit code from your authenticator app'
                    : state.selectedMethod === 'email'
                    ? `Enter the 6-digit code sent to ${userEmail}`
                    : `Enter the 6-digit code sent to your phone`}
                </p>
                
                <CodeInput
                  value={code}
                  onChange={setCode}
                  error={error}
                />
              </div>

              {(state.selectedMethod === 'email' || state.selectedMethod === 'sms') && (
                <p className="text-center text-sm text-gray-500">
                  Didn't receive a code?{' '}
                  <button
                    onClick={() => state.selectedMethod === 'email' ? onSendEmailCode() : onSendSMSCode()}
                    className="text-primary-600 hover:text-primary-700 font-medium"
                  >
                    Resend
                  </button>
                </p>
              )}

              <button
                onClick={handleVerify}
                disabled={code.length < 6 || isLoading}
                className="w-full py-2 px-4 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg disabled:opacity-50"
              >
                {isLoading ? 'Verifying...' : 'Verify'}
              </button>
            </div>
          )}

          {/* Step 4: Backup Codes */}
          {state.step === 'backup-codes' && state.backupCodes && (
            <div className="space-y-6">
              <BackupCodesDisplay
                codes={state.backupCodes}
                onCopy={handleCopyBackupCodes}
                onDownload={handleDownloadBackupCodes}
                onPrint={handlePrintBackupCodes}
              />

              <button
                onClick={() => setState({ ...state, step: 'complete' })}
                className="w-full py-2 px-4 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg"
              >
                I've saved my backup codes
              </button>
            </div>
          )}

          {/* Step 5: Complete */}
          {state.step === 'complete' && (
            <div className="text-center space-y-6">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full">
                <CheckCircle className="h-8 w-8 text-green-600 dark:text-green-400" />
              </div>
              
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Two-Factor Authentication Enabled
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
                  Your account is now more secure. You'll be asked to enter a verification code when signing in.
                </p>
              </div>

              <button
                onClick={() => {
                  onComplete();
                  onClose();
                }}
                className="w-full py-2 px-4 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg"
              >
                Done
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default MFASetupModal;
