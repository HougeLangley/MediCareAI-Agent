/** 医生端 API 服务层 */

import { API_BASE, authHeaders } from './client';

export interface PatientSummary {
  id: string;
  name: string;
  avatar?: string;
  last_activity: string;
  agent_summary: string;
  status: 'pending' | 'followup' | 'stable';
  risk_level?: 'low' | 'medium' | 'high';
}

export interface CaseDetail {
  id: string;
  patient_id: string;
  patient_name: string;
  title: string;
  description: string;
  diagnosis?: string;
  agent_summary?: string;
  structured_report?: Record<string, unknown>;
  comments: Array<{
    id: string;
    author: string;
    content: string;
    created_at: string;
  }>;
  created_at: string;
  updated_at: string;
}

export interface DoctorStats {
  pending_count: number;
  new_messages: number;
  followup_due: number;
  data_shares: number;
}

export async function fetchDashboardStats(): Promise<DoctorStats> {
  const res = await fetch(`${API_BASE}/doctor/stats`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Failed to fetch stats');
  return res.json();
}

export async function listPatients(): Promise<PatientSummary[]> {
  const res = await fetch(`${API_BASE}/doctor/cases`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Failed to fetch patients');
  return res.json();
}

export async function getCaseDetail(caseId: string): Promise<CaseDetail> {
  const res = await fetch(`${API_BASE}/doctor/cases/${caseId}`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Failed to fetch case detail');
  return res.json();
}

export async function addComment(caseId: string, content: string): Promise<void> {
  const res = await fetch(`${API_BASE}/doctor/cases/${caseId}/comment`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ content }),
  });
  if (!res.ok) throw new Error('Failed to add comment');
}

export async function sendPlanInstruction(caseId: string, instruction: string): Promise<{
  tasks_created: Array<{
    description: string;
    due_date?: string;
  }>;
  message: string;
}> {
  const res = await fetch(`${API_BASE}/doctor/cases/${caseId}/plan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ instruction }),
  });
  if (!res.ok) throw new Error('Failed to send instruction');
  return res.json();
}
