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
  chronic_diseases?: string[];
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
  const res = await fetch(`${API_BASE}/patient/care-plans/${planId}/ack`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ task_id: taskId }),
  });
  if (!res.ok) throw new Error('Failed to ack task');
}
