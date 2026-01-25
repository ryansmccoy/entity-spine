import { useState, useRef, useEffect } from 'react';
import {
  Inbox,
  Send,
  Search,
  Star,
  Trash2,
  Archive,
  Paperclip,
  CheckCheck,
  Check,
  ChevronLeft,
  Users,
  Plus,
  X,
} from 'lucide-react';
import { clsx } from 'clsx';
import { format, isToday, isYesterday } from 'date-fns';

// Types
interface UserInfo {
  id: string;
  name: string;
  email: string;
  avatarUrl?: string;
  status?: 'online' | 'offline';
}

interface Attachment {
  id: string;
  name: string;
  size: number;
  type: string;
  url: string;
}

interface Message {
  id: string;
  threadId: string;
  senderId: string;
  content: string;
  timestamp: Date;
  read: boolean;
  readAt?: Date;
  attachments?: Attachment[];
}

interface Thread {
  id: string;
  participants: UserInfo[];
  subject?: string;
  lastMessage: Message;
  unreadCount: number;
  starred: boolean;
  archived: boolean;
}

interface MessagingPageProps {
  currentUser: UserInfo;
  threads: Thread[];
  selectedThread?: Thread;
  messages: Message[];
  availableUsers: UserInfo[];
  isLoadingThreads?: boolean;
  isLoadingMessages?: boolean;
  onSelectThread: (threadId: string) => void;
  onSendMessage: (threadId: string, content: string, attachments?: File[]) => Promise<void>;
  onCreateThread: (userIds: string[], subject?: string, content?: string) => Promise<string>;
  onToggleStar: (threadId: string) => void;
  onArchiveThread: (threadId: string) => void;
  onDeleteThread: (threadId: string) => void;
  onMarkAsRead: (threadId: string) => void;
}

// Format message timestamp
function formatMessageTime(date: Date): string {
  if (isToday(date)) {
    return format(date, 'h:mm a');
  } else if (isYesterday(date)) {
    return 'Yesterday';
  } else {
    return format(date, 'MMM d');
  }
}

// Thread item component
function ThreadItem({
  thread,
  currentUserId,
  isSelected,
  onClick,
  onStar,
}: {
  thread: Thread;
  currentUserId: string;
  isSelected: boolean;
  onClick: () => void;
  onStar: () => void;
}) {
  const otherParticipants = thread.participants.filter(p => p.id !== currentUserId);
  const displayName = otherParticipants.length === 1
    ? otherParticipants[0].name
    : otherParticipants.map(p => p.name.split(' ')[0]).join(', ');

  return (
    <div
      onClick={onClick}
      className={clsx(
        'flex items-start gap-3 p-3 cursor-pointer transition-colors',
        isSelected
          ? 'bg-primary-50 dark:bg-primary-900/20 border-l-2 border-primary-500'
          : 'hover:bg-gray-50 dark:hover:bg-gray-800/50 border-l-2 border-transparent'
      )}
    >
      {/* Avatar */}
      <div className="relative flex-shrink-0">
        {otherParticipants.length === 1 ? (
          otherParticipants[0].avatarUrl ? (
            <img
              src={otherParticipants[0].avatarUrl}
              alt={otherParticipants[0].name}
              className="w-10 h-10 rounded-full"
            />
          ) : (
            <div className="w-10 h-10 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-sm font-medium text-gray-600 dark:text-gray-300">
              {otherParticipants[0].name.charAt(0)}
            </div>
          )
        ) : (
          <div className="w-10 h-10 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center">
            <Users className="h-5 w-5 text-gray-500" />
          </div>
        )}
        {otherParticipants.length === 1 && otherParticipants[0].status === 'online' && (
          <div className="absolute bottom-0 right-0 w-3 h-3 bg-green-500 border-2 border-white dark:border-gray-800 rounded-full" />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between">
          <span className={clsx(
            'text-sm truncate',
            thread.unreadCount > 0 ? 'font-semibold text-gray-900 dark:text-white' : 'text-gray-700 dark:text-gray-300'
          )}>
            {displayName}
          </span>
          <span className="text-xs text-gray-400 flex-shrink-0 ml-2">
            {formatMessageTime(thread.lastMessage.timestamp)}
          </span>
        </div>
        {thread.subject && (
          <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{thread.subject}</p>
        )}
        <p className={clsx(
          'text-sm truncate mt-0.5',
          thread.unreadCount > 0 ? 'text-gray-700 dark:text-gray-200' : 'text-gray-500 dark:text-gray-400'
        )}>
          {thread.lastMessage.senderId === currentUserId ? 'You: ' : ''}
          {thread.lastMessage.content}
        </p>
      </div>

      {/* Indicators */}
      <div className="flex flex-col items-end gap-1">
        {thread.unreadCount > 0 && (
          <span className="w-5 h-5 flex items-center justify-center text-xs font-medium text-white bg-primary-500 rounded-full">
            {thread.unreadCount > 9 ? '9+' : thread.unreadCount}
          </span>
        )}
        <button
          onClick={(e) => { e.stopPropagation(); onStar(); }}
          className={clsx(
            'p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700',
            thread.starred ? 'text-yellow-500' : 'text-gray-300 hover:text-gray-400'
          )}
        >
          {thread.starred ? <Star className="h-4 w-4 fill-current" /> : <Star className="h-4 w-4" />}
        </button>
      </div>
    </div>
  );
}

// Message bubble component
function MessageBubble({
  message,
  isOwn,
  senderInfo,
  showAvatar,
}: {
  message: Message;
  isOwn: boolean;
  senderInfo?: UserInfo;
  showAvatar: boolean;
}) {
  return (
    <div className={clsx('flex gap-2', isOwn ? 'flex-row-reverse' : 'flex-row')}>
      {/* Avatar placeholder or avatar */}
      <div className="w-8 flex-shrink-0">
        {showAvatar && !isOwn && senderInfo && (
          senderInfo.avatarUrl ? (
            <img
              src={senderInfo.avatarUrl}
              alt={senderInfo.name}
              className="w-8 h-8 rounded-full"
            />
          ) : (
            <div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-xs font-medium text-gray-600 dark:text-gray-300">
              {senderInfo.name.charAt(0)}
            </div>
          )
        )}
      </div>

      {/* Message content */}
      <div className={clsx('max-w-[70%]', isOwn ? 'items-end' : 'items-start')}>
        <div
          className={clsx(
            'px-4 py-2 rounded-2xl',
            isOwn
              ? 'bg-primary-500 text-white rounded-br-md'
              : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white rounded-bl-md'
          )}
        >
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
          
          {/* Attachments */}
          {message.attachments && message.attachments.length > 0 && (
            <div className="mt-2 space-y-1">
              {message.attachments.map((att) => (
                <a
                  key={att.id}
                  href={att.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={clsx(
                    'flex items-center gap-2 text-xs underline',
                    isOwn ? 'text-white/80' : 'text-primary-600 dark:text-primary-400'
                  )}
                >
                  <Paperclip className="h-3 w-3" />
                  {att.name}
                </a>
              ))}
            </div>
          )}
        </div>

        {/* Timestamp and status */}
        <div className={clsx('flex items-center gap-1 mt-1 text-xs text-gray-400', isOwn && 'justify-end')}>
          <span>{format(message.timestamp, 'h:mm a')}</span>
          {isOwn && (
            message.read ? (
              <CheckCheck className="h-3 w-3 text-primary-500" />
            ) : (
              <Check className="h-3 w-3" />
            )
          )}
        </div>
      </div>
    </div>
  );
}

// New message modal
function NewMessageModal({
  isOpen,
  onClose,
  availableUsers,
  onSend,
}: {
  isOpen: boolean;
  onClose: () => void;
  availableUsers: UserInfo[];
  onSend: (userIds: string[], subject: string, content: string) => void;
}) {
  const [selectedUsers, setSelectedUsers] = useState<UserInfo[]>([]);
  const [subject, setSubject] = useState('');
  const [content, setContent] = useState('');
  const [search, setSearch] = useState('');

  if (!isOpen) return null;

  const filteredUsers = availableUsers.filter(
    (u) =>
      !selectedUsers.find(s => s.id === u.id) &&
      (u.name.toLowerCase().includes(search.toLowerCase()) ||
        u.email.toLowerCase().includes(search.toLowerCase()))
  );

  const handleSend = () => {
    if (selectedUsers.length === 0 || !content.trim()) return;
    onSend(selectedUsers.map(u => u.id), subject, content);
    onClose();
    setSelectedUsers([]);
    setSubject('');
    setContent('');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-xl max-w-lg w-full mx-4">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
          <h3 className="font-semibold text-gray-900 dark:text-white">New Message</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-4 space-y-4">
          {/* Recipients */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              To
            </label>
            <div className="flex flex-wrap gap-2 p-2 border border-gray-200 dark:border-gray-700 rounded-lg min-h-[42px]">
              {selectedUsers.map((user) => (
                <span
                  key={user.id}
                  className="flex items-center gap-1 px-2 py-1 bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded text-sm"
                >
                  {user.name}
                  <button
                    onClick={() => setSelectedUsers(selectedUsers.filter(u => u.id !== user.id))}
                    className="hover:text-primary-900"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder={selectedUsers.length === 0 ? 'Search users...' : ''}
                className="flex-1 min-w-[120px] text-sm bg-transparent outline-none"
              />
            </div>
            {search && filteredUsers.length > 0 && (
              <div className="absolute mt-1 w-full max-h-40 overflow-y-auto bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-10">
                {filteredUsers.map((user) => (
                  <button
                    key={user.id}
                    onClick={() => {
                      setSelectedUsers([...selectedUsers, user]);
                      setSearch('');
                    }}
                    className="w-full flex items-center gap-3 p-2 hover:bg-gray-50 dark:hover:bg-gray-700/50 text-left"
                  >
                    {user.avatarUrl ? (
                      <img src={user.avatarUrl} alt={user.name} className="w-8 h-8 rounded-full" />
                    ) : (
                      <div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-sm">
                        {user.name.charAt(0)}
                      </div>
                    )}
                    <div>
                      <p className="text-sm font-medium text-gray-900 dark:text-white">{user.name}</p>
                      <p className="text-xs text-gray-500">{user.email}</p>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Subject */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Subject (optional)
            </label>
            <input
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="Message subject..."
              className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          {/* Message */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Message
            </label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Write your message..."
              rows={4}
              className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 outline-none focus:ring-2 focus:ring-primary-500 resize-none"
            />
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
          >
            Cancel
          </button>
          <button
            onClick={handleSend}
            disabled={selectedUsers.length === 0 || !content.trim()}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-lg disabled:opacity-50"
          >
            <Send className="h-4 w-4" />
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

// Inner component (used by the wrapper)
function MessagingPageInner({
  currentUser,
  threads,
  selectedThread,
  messages,
  availableUsers,
  isLoadingThreads,
  isLoadingMessages,
  onSelectThread,
  onSendMessage,
  onCreateThread,
  onToggleStar,
  onArchiveThread,
  onDeleteThread,
  onMarkAsRead: _onMarkAsRead,
}: MessagingPageProps) {
  // Note: _onMarkAsRead will be used when implementing automatic read marking
  void _onMarkAsRead;
  
  const [showNewMessage, setShowNewMessage] = useState(false);
  const [newMessage, setNewMessage] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [filter, setFilter] = useState<'all' | 'unread' | 'starred'>('all');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Filter threads
  const filteredThreads = threads
    .filter((t) => !t.archived)
    .filter((t) => {
      if (filter === 'unread') return t.unreadCount > 0;
      if (filter === 'starred') return t.starred;
      return true;
    })
    .filter((t) => {
      if (!searchQuery) return true;
      const names = t.participants.map(p => p.name.toLowerCase()).join(' ');
      return names.includes(searchQuery.toLowerCase()) ||
        t.lastMessage.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
        t.subject?.toLowerCase().includes(searchQuery.toLowerCase());
    });

  const handleSendMessage = async () => {
    if (!selectedThread || !newMessage.trim()) return;
    await onSendMessage(selectedThread.id, newMessage.trim());
    setNewMessage('');
  };

  const handleNewMessage = async (userIds: string[], subject: string, content: string) => {
    await onCreateThread(userIds, subject, content);
  };

  const otherParticipants = selectedThread
    ? selectedThread.participants.filter(p => p.id !== currentUser.id)
    : [];

  return (
    <div className="flex h-[calc(100vh-120px)] bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      {/* Thread List */}
      <div className={clsx(
        'w-80 flex-shrink-0 border-r border-gray-200 dark:border-gray-700 flex flex-col',
        selectedThread && 'hidden md:flex'
      )}>
        {/* Header */}
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <Inbox className="h-5 w-5 text-primary-500" />
              Messages
            </h2>
            <button
              onClick={() => setShowNewMessage(true)}
              className="p-2 text-primary-600 hover:bg-primary-50 dark:hover:bg-primary-900/20 rounded-lg"
            >
              <Plus className="h-5 w-5" />
            </button>
          </div>
          
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search messages..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-sm bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          <div className="flex items-center gap-1 mt-3">
            {(['all', 'unread', 'starred'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={clsx(
                  'px-3 py-1 text-xs font-medium rounded-full transition-colors',
                  filter === f
                    ? 'bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400'
                    : 'text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800'
                )}
              >
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Thread List */}
        <div className="flex-1 overflow-y-auto">
          {isLoadingThreads ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin h-6 w-6 border-2 border-primary-500 border-t-transparent rounded-full" />
            </div>
          ) : filteredThreads.length > 0 ? (
            filteredThreads.map((thread) => (
              <ThreadItem
                key={thread.id}
                thread={thread}
                currentUserId={currentUser.id}
                isSelected={selectedThread?.id === thread.id}
                onClick={() => onSelectThread(thread.id)}
                onStar={() => onToggleStar(thread.id)}
              />
            ))
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-gray-500 dark:text-gray-400">
              <Inbox className="h-12 w-12 mb-3 opacity-50" />
              <p className="text-sm">No messages</p>
              <button
                onClick={() => setShowNewMessage(true)}
                className="mt-2 text-sm text-primary-600 hover:text-primary-700 font-medium"
              >
                Start a conversation
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Message View */}
      {selectedThread ? (
        <div className="flex-1 flex flex-col">
          {/* Header */}
          <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-200 dark:border-gray-700">
            <button
              onClick={() => onSelectThread('')}
              className="md:hidden p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
            >
              <ChevronLeft className="h-5 w-5 text-gray-500" />
            </button>
            
            {otherParticipants.length === 1 ? (
              <>
                {otherParticipants[0].avatarUrl ? (
                  <img
                    src={otherParticipants[0].avatarUrl}
                    alt={otherParticipants[0].name}
                    className="w-10 h-10 rounded-full"
                  />
                ) : (
                  <div className="w-10 h-10 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-sm font-medium">
                    {otherParticipants[0].name.charAt(0)}
                  </div>
                )}
                <div className="flex-1">
                  <p className="font-medium text-gray-900 dark:text-white">{otherParticipants[0].name}</p>
                  <p className="text-xs text-gray-500">{otherParticipants[0].status === 'online' ? 'Online' : 'Offline'}</p>
                </div>
              </>
            ) : (
              <>
                <div className="w-10 h-10 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center">
                  <Users className="h-5 w-5 text-gray-500" />
                </div>
                <div className="flex-1">
                  <p className="font-medium text-gray-900 dark:text-white">
                    {otherParticipants.map(p => p.name.split(' ')[0]).join(', ')}
                  </p>
                  <p className="text-xs text-gray-500">{otherParticipants.length + 1} participants</p>
                </div>
              </>
            )}

            <div className="flex items-center gap-1">
              <button
                onClick={() => onToggleStar(selectedThread.id)}
                className={clsx(
                  'p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800',
                  selectedThread.starred ? 'text-yellow-500' : 'text-gray-400'
                )}
              >
                <Star className={clsx('h-5 w-5', selectedThread.starred && 'fill-current')} />
              </button>
              <button
                onClick={() => onArchiveThread(selectedThread.id)}
                className="p-2 text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
              >
                <Archive className="h-5 w-5" />
              </button>
              <button
                onClick={() => onDeleteThread(selectedThread.id)}
                className="p-2 text-gray-400 hover:text-red-500 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
              >
                <Trash2 className="h-5 w-5" />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {isLoadingMessages ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin h-6 w-6 border-2 border-primary-500 border-t-transparent rounded-full" />
              </div>
            ) : (
              messages.map((message, index) => {
                const isOwn = message.senderId === currentUser.id;
                const sender = selectedThread.participants.find(p => p.id === message.senderId);
                const showAvatar = !isOwn && (index === 0 || messages[index - 1].senderId !== message.senderId);
                
                return (
                  <MessageBubble
                    key={message.id}
                    message={message}
                    isOwn={isOwn}
                    senderInfo={sender}
                    showAvatar={showAvatar}
                  />
                );
              })
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Compose */}
          <div className="p-4 border-t border-gray-200 dark:border-gray-700">
            <div className="flex items-end gap-2">
              <div className="flex-1">
                <textarea
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSendMessage();
                    }
                  }}
                  placeholder="Type a message..."
                  rows={1}
                  className="w-full px-4 py-2 text-sm bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl outline-none focus:ring-2 focus:ring-primary-500 resize-none"
                />
              </div>
              <button
                onClick={handleSendMessage}
                disabled={!newMessage.trim()}
                className="p-2 text-white bg-primary-600 hover:bg-primary-700 rounded-xl disabled:opacity-50"
              >
                <Send className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="flex-1 hidden md:flex items-center justify-center">
          <div className="text-center text-gray-500 dark:text-gray-400">
            <Inbox className="h-16 w-16 mx-auto mb-4 opacity-50" />
            <p className="text-lg font-medium">Select a conversation</p>
            <p className="text-sm mt-1">Or start a new one</p>
            <button
              onClick={() => setShowNewMessage(true)}
              className="mt-4 flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-lg mx-auto"
            >
              <Plus className="h-4 w-4" />
              New Message
            </button>
          </div>
        </div>
      )}

      {/* New Message Modal */}
      <NewMessageModal
        isOpen={showNewMessage}
        onClose={() => setShowNewMessage(false)}
        availableUsers={availableUsers}
        onSend={handleNewMessage}
      />
    </div>
  );
}

// Sample data for development
const sampleCurrentUser: UserInfo = {
  id: 'user-1',
  name: 'John Smith',
  email: 'john@example.com',
  status: 'online',
};

const sampleUsers: UserInfo[] = [
  sampleCurrentUser,
  { id: 'user-2', name: 'Sarah Johnson', email: 'sarah@example.com', status: 'online' },
  { id: 'user-3', name: 'Mike Brown', email: 'mike@example.com', status: 'offline' },
  { id: 'user-4', name: 'Emily Davis', email: 'emily@example.com', status: 'online' },
  { id: 'user-5', name: 'Robert Wilson', email: 'robert@example.com', status: 'offline' },
];

const generateSampleMessages = (threadId: string, participantIds: string[]): Message[] => {
  const messages: Message[] = [];
  const contents = [
    'Hey, did you see the latest 10-K filing from Apple?',
    'Yes! The revenue growth is impressive.',
    'I noticed some interesting changes in their risk factors section.',
    'We should probably set up an alert for their next 8-K.',
    'Good idea. I\'ll create one for material events.',
    'Thanks! Let me know if you need help with the analysis.',
    'Will do. Also, check out the new dashboard features.',
    'Already did - the feed management is much better now.',
  ];

  for (let i = 0; i < 8; i++) {
    const senderId = participantIds[i % 2];
    messages.push({
      id: `msg-${threadId}-${i}`,
      threadId,
      senderId,
      content: contents[i],
      timestamp: new Date(Date.now() - (8 - i) * 15 * 60 * 1000),
      read: true,
    });
  }

  return messages;
};

const sampleThreads: Thread[] = [
  {
    id: 'thread-1',
    participants: [sampleUsers[0], sampleUsers[1]],
    subject: 'Apple 10-K Analysis',
    lastMessage: {
      id: 'msg-thread-1-7',
      threadId: 'thread-1',
      senderId: 'user-2',
      content: 'Already did - the feed management is much better now.',
      timestamp: new Date(Date.now() - 5 * 60 * 1000),
      read: false,
    },
    unreadCount: 2,
    starred: true,
    archived: false,
  },
  {
    id: 'thread-2',
    participants: [sampleUsers[0], sampleUsers[2]],
    lastMessage: {
      id: 'msg-thread-2-1',
      threadId: 'thread-2',
      senderId: 'user-1',
      content: 'Can you review the quarterly report?',
      timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000),
      read: true,
    },
    unreadCount: 0,
    starred: false,
    archived: false,
  },
  {
    id: 'thread-3',
    participants: [sampleUsers[0], sampleUsers[3], sampleUsers[4]],
    subject: 'Team Updates',
    lastMessage: {
      id: 'msg-thread-3-1',
      threadId: 'thread-3',
      senderId: 'user-4',
      content: 'Meeting at 3pm tomorrow for the new feature demo.',
      timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000),
      read: true,
    },
    unreadCount: 0,
    starred: false,
    archived: false,
  },
];

// Page wrapper with sample data
export function MessagingPage() {
  const [threads, setThreads] = useState(sampleThreads);
  const [selectedThreadId, setSelectedThreadId] = useState<string | undefined>();
  const [messages, setMessages] = useState<Message[]>([]);

  const selectedThread = threads.find(t => t.id === selectedThreadId);

  const handleSelectThread = (threadId: string) => {
    setSelectedThreadId(threadId);
    const thread = threads.find(t => t.id === threadId);
    if (thread) {
      const participantIds = thread.participants.map(p => p.id);
      setMessages(generateSampleMessages(threadId, participantIds));
      // Mark as read
      setThreads(prev => prev.map(t => 
        t.id === threadId ? { ...t, unreadCount: 0 } : t
      ));
    }
  };

  const handleSendMessage = async (threadId: string, content: string) => {
    const newMessage: Message = {
      id: `msg-${Date.now()}`,
      threadId,
      senderId: sampleCurrentUser.id,
      content,
      timestamp: new Date(),
      read: false,
    };
    setMessages(prev => [...prev, newMessage]);
    setThreads(prev => prev.map(t =>
      t.id === threadId ? { ...t, lastMessage: newMessage } : t
    ));
  };

  const handleCreateThread = async (userIds: string[], subject?: string, content?: string) => {
    const participants = [sampleCurrentUser, ...sampleUsers.filter(u => userIds.includes(u.id))];
    const newThread: Thread = {
      id: `thread-${Date.now()}`,
      participants,
      subject,
      lastMessage: {
        id: `msg-${Date.now()}`,
        threadId: `thread-${Date.now()}`,
        senderId: sampleCurrentUser.id,
        content: content || '',
        timestamp: new Date(),
        read: false,
      },
      unreadCount: 0,
      starred: false,
      archived: false,
    };
    setThreads(prev => [newThread, ...prev]);
    setSelectedThreadId(newThread.id);
    if (content) {
      setMessages([newThread.lastMessage]);
    }
    return newThread.id;
  };

  const handleToggleStar = (threadId: string) => {
    setThreads(prev => prev.map(t =>
      t.id === threadId ? { ...t, starred: !t.starred } : t
    ));
  };

  const handleArchiveThread = (threadId: string) => {
    setThreads(prev => prev.map(t =>
      t.id === threadId ? { ...t, archived: true } : t
    ));
    if (selectedThreadId === threadId) {
      setSelectedThreadId(undefined);
    }
  };

  const handleDeleteThread = (threadId: string) => {
    setThreads(prev => prev.filter(t => t.id !== threadId));
    if (selectedThreadId === threadId) {
      setSelectedThreadId(undefined);
    }
  };

  const handleMarkAsRead = (threadId: string) => {
    setThreads(prev => prev.map(t =>
      t.id === threadId ? { ...t, unreadCount: 0 } : t
    ));
  };

  return (
    <div className="p-6">
      <MessagingPageInner
        currentUser={sampleCurrentUser}
        threads={threads}
        selectedThread={selectedThread}
        messages={messages}
        availableUsers={sampleUsers.filter(u => u.id !== sampleCurrentUser.id)}
        onSelectThread={handleSelectThread}
        onSendMessage={handleSendMessage}
        onCreateThread={handleCreateThread}
        onToggleStar={handleToggleStar}
        onArchiveThread={handleArchiveThread}
        onDeleteThread={handleDeleteThread}
        onMarkAsRead={handleMarkAsRead}
      />
    </div>
  );
}

export default MessagingPage;
