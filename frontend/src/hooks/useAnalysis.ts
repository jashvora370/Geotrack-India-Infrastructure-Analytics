'use client';

import { useState, useCallback, useRef } from 'react';
import { api } from '@/lib/api';
import type { AnalysisJob } from '@/lib/types';

const POLL_INTERVAL_MS = 2000;
const MAX_POLLS = 150; // 5 minutes

export function useAnalysis() {
  const [job, setJob] = useState<AnalysisJob | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pollCountRef = useRef(0);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearTimeout(pollRef.current);
      pollRef.current = null;
    }
    pollCountRef.current = 0;
  }, []);

  const pollStatus = useCallback(
    async (jobId: string) => {
      try {
        const status = await api.roadNetwork.getJobStatus(jobId);
        setJob(status);

        if (status.status === 'completed' || status.status === 'failed') {
          stopPolling();
          if (status.status === 'failed') {
            setError('Analysis job failed. Please try again.');
          }
          return;
        }

        pollCountRef.current += 1;
        if (pollCountRef.current >= MAX_POLLS) {
          stopPolling();
          setError('Analysis timed out. Please try again.');
          return;
        }

        pollRef.current = setTimeout(
          () => pollStatus(jobId),
          POLL_INTERVAL_MS
        );
      } catch (err) {
        stopPolling();
        setError(err instanceof Error ? err.message : 'Failed to poll analysis status');
      }
    },
    [stopPolling]
  );

  const runAnalysis = useCallback(
    async (region: string, bbox: number[], years: number[]) => {
      setIsSubmitting(true);
      setError(null);
      setJob(null);
      stopPolling();

      try {
        const newJob = await api.roadNetwork.analyze(region, bbox, years);
        setJob(newJob);

        if (newJob.status !== 'completed' && newJob.status !== 'failed') {
          pollRef.current = setTimeout(
            () => pollStatus(newJob.jobId),
            POLL_INTERVAL_MS
          );
        }
      } catch (err) {
        setError(
          err instanceof Error ? err.message : 'Failed to start analysis'
        );
      } finally {
        setIsSubmitting(false);
      }
    },
    [stopPolling, pollStatus]
  );

  const reset = useCallback(() => {
    stopPolling();
    setJob(null);
    setError(null);
    setIsSubmitting(false);
  }, [stopPolling]);

  return {
    job,
    isSubmitting,
    isRunning: job?.status === 'queued' || job?.status === 'running',
    isCompleted: job?.status === 'completed',
    isFailed: job?.status === 'failed',
    progress: job?.progress ?? 0,
    error,
    runAnalysis,
    reset,
  };
}
