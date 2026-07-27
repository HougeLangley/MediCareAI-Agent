/** 患者端 API 服务层 */

import { API_BASE } from './client';

import { authHeaders } from './client';

export interface PatientProfile {
  id: string;
  name: string;
  email: string;
  phone?: string;
  date_of_birth?: string;
  gender?: string;
  height?: number;
  weight?: number;
  allergies?: string[];
  chronic_diseases?: { code: string; name: string }[];
  medications?: Array<{
    name: string;
    dosage: string;
    frequency: string;
    start_date?: string;
  }>;
}

export interface MedicalCase {
  id: string;
  title: string;
  description: string;
  status: string;
  created_at: string;
  diagnosis?: string;
}

export interface CarePlan {
  id: string;
  title: string;
  goals: string[];
  tasks: Array<{
    id: string;
    description: string;
    due_date?: string;
    completed: boolean;
  }>;
  start_date: string;
  end_date?: string;
}

export async function getProfile(): Promise<PatientProfile> {
  const res = await fetch(`${API_BASE}/patient/profile`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Failed to fetch profile');
  return res.json();
}

export async function updateProfile(data: Partial<PatientProfile>): Promise<PatientProfile> {
  const res = await fetch(`${API_BASE}/patient/profile`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to update profile');
  return res.json();
}

export async function listCases(): Promise<MedicalCase[]> {
  const res = await fetch(`${API_BASE}/patient/cases`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Failed to fetch cases');
  return res.json();
}

export async function listCarePlans(): Promise<CarePlan[]> {
  const res = await fetch(`${API_BASE}/patient/care-plans`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Failed to fetch care plans');
  return res.json();
}

export async function ackTask(planId: string, taskId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/patient/care-plans/${planId}/ack?task_id=${encodeURIComponent(taskId)}`, {
    method: 'POST',
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error('Failed to ack task');
}

export async function getReminderCount(): Promise<{ follow_up: number; medication: number; total: number }> {
  const res = await fetch(`${API_BASE}/patient/reminders/count`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Failed to fetch reminder count');
  return res.json();
}

export async function listReminders(): Promise<unknown[]> {
  const res = await fetch(`${API_BASE}/patient/reminders`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Failed to fetch reminders');
  return res.json();
}

export async function acknowledgeReminder(reminderId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/patient/reminders/${reminderId}/ack`, {
    method: 'POST',
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error('Failed to acknowledge reminder');
}
