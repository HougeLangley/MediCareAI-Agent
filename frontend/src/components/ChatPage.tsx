import { useState, useRef, useEffect, useCallback, useLayoutEffect } from 'react';
import {
  Box,
  CssBaseline,
  AppBar,
  Toolbar,
  IconButton,
  Typography,
  Fab,
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import type { ChatMessageItem, ChatSession, GuestStatus, SSEEvent, DiagnosisReport, WorkflowStep } from '../types/agent';
import { agentApi } from '../api/agent';
import { getToken } from '../api/client';
import Sidebar from './Sidebar';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import GuestBanner from './GuestBanner';
import { flexRowGap05 } from '../styles/sxUtils';


const QUICK_REPLIES = [
  '头疼还发烧',
  '腹痛拉肚子',
  '咳嗽一周了',
  '近期体检报告解读',
];

function generateId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
}

export default function ChatPage() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string>();
  const [messages, setMessages] = useState<ChatMessageItem[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [guestStatus, setGuestStatus] = useState<GuestStatus | null>(null);
  const [showScrollDown, setShowScrollDown] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const didInit = useRef(false);

  // 初始化：检查认证状态，未登录时自动创建访客 session
  useEffect(() => {
    if (didInit.current) return;
    didInit.current = true;

    const initAuth = async () => {
      const stored = agentApi.getGuestStatus();
      if (stored) {
        setGuestStatus(stored);
        return;
      }
      if (!getToken()) {
        // 未登录，尝试创建访客 session
        try {
          await agentApi.createGuestSession();
          setGuestStatus(agentApi.getGuestStatus());
        } catch (e) {
          console.error('Failed to create guest session on ChatPage init:', e);
        }
      }
    };

    initAuth();
  }, []);

  // 滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 滚动监听
  const handleScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 100;
    setShowScrollDown(!nearBottom);
  }, []);

  // 创建新对话
  const startNewSession = useCallback(() => {
    const id = generateId();
    const newSession: ChatSession = {
      id,
      title: '新对话',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      message_count: 0,
    };
    setSessions((prev) => [newSession, ...prev]);
    setCurrentSessionId(id);
    setMessages([
      {
        id: generateId(),
        role: 'agent',
        content: `您好！我是 MediCareAI 智能医疗助手🩺\n\n我可以帮您：\n• 分析症状并给出初步诊断\n• 解读检查报告\n• 提供健康建议\n\n请描述您的不适感受，或上传相关检查报告。`,
        timestamp: new Date(),
      },
    ]);
  }, []);

  // 初始化：使用 useLayoutEffect + setTimeout 将 setState 延迟到下一个 tick
  useLayoutEffect(() => {
    if (sessions.length > 0) return;
    const timer = setTimeout(() => {
      startNewSession();
    }, 0);
    return () => clearTimeout(timer);
  }, [sessions.length, startNewSession]);

  const handleSend = useCallback(
    async (text: string) => {
      if (isStreaming || !currentSessionId) return;

      const userMsg: ChatMessageItem = {
        id: generateId(),
        role: 'user',
        content: text,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMsg]);

      setIsStreaming(true);
      const agentMsgId = generateId();
      let content = '';
      let structured: DiagnosisReport | undefined;
      const workflowSteps: WorkflowStep[] = [];

      // Build patient history from previous messages for context
      const patientHistory = messages
        .filter(m => m.role === 'user' || m.role === 'agent')
        .map(m => `${m.role === 'user' ? '患者' : '医生'}: ${m.content}`)
        .join('\n');

      // 工作流步骤辅助函数
      const addStep = (step: Omit<WorkflowStep, 'id' | 'timestamp'>) => {
        const newStep: WorkflowStep = { ...step, id: generateId(), timestamp: new Date() };
        workflowSteps.push(newStep);
        setMessages((prev) => {
          const idx = prev.findIndex((m) => m.id === agentMsgId);
          if (idx === -1) {
            return [...prev, { id: agentMsgId, role: 'agent', content: '', timestamp: new Date(), isStreaming: true, workflowSteps: [...workflowSteps] }];
          }
          const next = prev.slice();
          next[idx] = { ...next[idx], workflowSteps: [...workflowSteps] };
          return next;
        });
      };

      try {
        await agentApi.streamDiagnose(
          { message: text, session_id: currentSessionId, patient_history: patientHistory },
          (event: SSEEvent) => {
            switch (event.event) {
              case 'intent': {
                const intent = event.data?.intent as string || 'diagnosis';
                const confidence = event.data?.confidence as string || 'medium';
                const reasoning = event.data?.reasoning as string || '';
                addStep({
                  type: 'intent',
                  status: 'done',
                  title: `MasterAgent 识别到意图: ${intent}`,
                  detail: `置信度: ${confidence}${reasoning ? ` | ${reasoning}` : ''}`,
                });
                break;
              }
              case 'agent_switch': {
                const agentDisplay = event.data?.agent_display as string || event.data?.agent as string || '未知';
                addStep({
                  type: 'agent_switch',
                  status: 'done',
                  title: `已切换到 ${agentDisplay}`,
                  detail: event.data?.message as string || '',
                });
                break;
              }
              case 'thinking': {
                const stepName = event.data?.step as string || 'thinking';
                const messageText = event.data?.message as string || '正在分析...';
                addStep({
                  type: 'thinking',
                  status: 'done',
                  title: messageText,
                  detail: event.data?.detail as string || '',
                });
                break;
              }
              case 'tool_call': {
                const toolName = event.data?.tool as string || '未知工具';
                addStep({
                  type: 'tool_call',
                  status: 'done',
                  title: event.data?.message as string || `正在调用 ${toolName}...`,
                  toolName,
                  toolParams: (event.data?.params as Record<string, unknown>) || {},
                });
                break;
              }
              case 'tool_result': {
                const toolName = event.data?.tool as string || '未知工具';
                addStep({
                  type: 'tool_result',
                  status: 'done',
                  title: event.data?.message as string || `${toolName} 执行完成`,
                  toolName,
                  toolResult: event.data?.result,
                });
                break;
              }
              case 'text': {
                content += event.data?.text || '';
                setMessages((prev) => {
                  const idx = prev.findIndex((m) => m.id === agentMsgId);
                  if (idx === -1) {
                    return [...prev, { id: agentMsgId, role: 'agent', content, timestamp: new Date(), isStreaming: true, workflowSteps: [...workflowSteps] }];
                  }
                  const next = prev.slice();
                  next[idx] = { ...next[idx], content, isStreaming: true, workflowSteps: [...workflowSteps] };
                  return next;
                });
                break;
              }
              case 'structured':
                structured = event.data as unknown as DiagnosisReport;
                setMessages((prev) => {
                  const idx = prev.findIndex((m) => m.id === agentMsgId);
                  if (idx === -1) return prev;
                  const next = prev.slice();
                  next[idx] = { ...next[idx], structured, content: content || next[idx].content || '已生成诊断报告', workflowSteps: [...workflowSteps] };
                  return next;
                });
                break;
              case 'error': {
                const errorMsg = event.data?.message as string || event.data?.error as string || '服务异常';
                addStep({
                  type: 'thinking',
                  status: 'error',
                  title: `错误: ${errorMsg}`,
                });
                setMessages((prev) => {
                  const idx = prev.findIndex((m) => m.id === agentMsgId);
                  if (idx === -1) {
                    return [...prev, { id: agentMsgId, role: 'agent', content: `❌ 错误: ${errorMsg}`, timestamp: new Date(), workflowSteps: [...workflowSteps] }];
                  }
                  const next = prev.slice();
                  next[idx] = { ...next[idx], content: `❌ 错误: ${errorMsg}`, isStreaming: false, workflowSteps: [...workflowSteps] };
                  return next;
                });
                break;
              }
              case 'complete': {
                addStep({
                  type: 'complete',
                  status: 'done',
                  title: event.data?.message as string || '✅ 响应完成',
                });
                setMessages((prev) => {
                  const idx = prev.findIndex((m) => m.id === agentMsgId);
                  if (idx === -1) return prev;
                  const next = prev.slice();
                  next[idx] = { ...next[idx], isStreaming: false, workflowSteps: [...workflowSteps] };
                  return next;
                });
                setIsStreaming(false);
                break;
              }
            }
          }
        );
      } catch {
        setMessages((prev) => [...prev, { id: generateId(), role: 'agent', content: `❌ 连接失败，请检查网络后重试`, timestamp: new Date() }]);
        setIsStreaming(false);
      }
    },
    [isStreaming, currentSessionId]
  );

  return (
    <Box sx={{ display: 'flex', height: '100vh', bgcolor: '#FFFBF5' }}>
      <CssBaseline />
      <Sidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        onSelectSession={setCurrentSessionId}
        onNewSession={startNewSession}
        mobileOpen={mobileOpen}
        onMobileClose={() => setMobileOpen(false)}
      />

      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <AppBar position="static" elevation={0} sx={{ bgcolor: '#FFFBF5', borderBottom: '1px solid #F5E6D3', color: 'text.primary' }}>
          <Toolbar sx={{ minHeight: 56 }}>
            <IconButton edge="start" sx={{ mr: 2, display: { md: 'none' }, color: 'text.primary' }} onClick={() => setMobileOpen(true)}>
              <MenuIcon />
            </IconButton>
            <Typography variant="subtitle1" sx={{ flex: 1, fontWeight: 500 }}>
              {sessions.find((s) => s.id === currentSessionId)?.title || '智能医疗助手'}
            </Typography>
            <Box sx={flexRowGap05}>
              <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: 'success.main', mr: 0.5 }} />
              <Typography variant="caption" color="text.secondary">在线</Typography>
            </Box>
          </Toolbar>
        </AppBar>

        <GuestBanner
          status={guestStatus}
          onRegister={() => { /* TODO: 跳转注册页面 */ }}
          onLogin={() => { /* TODO: 跳转登录页面 */ }}
        />

        <Box
          ref={scrollRef}
          onScroll={handleScroll}
          sx={{
            flex: 1,
            overflow: 'auto',
            px: { xs: 1, sm: 2, md: 4 },
            py: 2,
            '&::-webkit-scrollbar': { width: 6 },
            '&::-webkit-scrollbar-thumb': { borderRadius: 3, bgcolor: '#F5E6D3' },
          }}
        >
          {messages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))}
          <div ref={messagesEndRef} />
        </Box>

        {showScrollDown && (
          <Fab size="small" color="primary" sx={{ position: 'absolute', bottom: 100, right: 24, bgcolor: 'primary.main', '&:hover': { bgcolor: 'primary.dark' } }}
            onClick={() => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })}>
            <KeyboardArrowDownIcon />
          </Fab>
        )}

        <Box sx={{ p: 2, borderTop: '1px solid #F5E6D3', bgcolor: 'background.paper' }}>
          <ChatInput
            onSend={handleSend}
            disabled={isStreaming}
            quickReplies={messages.length < 3 ? QUICK_REPLIES : undefined}
            onQuickReply={handleSend}
          />
        </Box>
      </Box>
    </Box>
  );
}