/**
 * Mock WebSocket Service
 * Backend hazır olana kadar kullanılacak mock WebSocket
 * Gerçekçi event akışı simülasyonu
 */

import type {
  WebSocketEvent,
  JobStartedEvent,
  JobCompletedEvent,
  AgentStartedEvent,
  AgentProgressEvent,
  AgentCompletedEvent,
  CouncilStartedEvent,
  CouncilPhaseChangedEvent,
  CouncilSpeakerChangedEvent,
  CouncilSpeechEvent,
  CouncilScoreRevisionEvent,
  CouncilDecisionEvent,
  AgentType,
} from '@/types';
import { MOCK_COUNCIL_MEMBERS, MOCK_TRANSCRIPT, delay } from './mockData';

// ==================== Types ====================

type EventCallback = (event: WebSocketEvent) => void;

interface MockWebSocketOptions {
  onEvent: EventCallback;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: string) => void;
  speed?: number; // 1 = normal, 2 = 2x hızlı, 0.5 = yarı hız
}

// ==================== Mock WebSocket Class ====================

export class MockWebSocket {
  private reportId: string;
  private companyName: string;
  private options: MockWebSocketOptions;
  private isRunning: boolean = false;
  private abortController: AbortController | null = null;

  constructor(
    reportId: string, 
    companyName: string,
    options: MockWebSocketOptions
  ) {
    this.reportId = reportId;
    this.companyName = companyName;
    this.options = {
      speed: 1,
      ...options,
    };
  }

  private get speedMultiplier(): number {
    return 1 / (this.options.speed || 1);
  }

  private async wait(ms: number): Promise<void> {
    if (!this.isRunning) return;
    await delay(ms * this.speedMultiplier);
  }

  private emit(event: WebSocketEvent): void {
    if (this.isRunning) {
      this.options.onEvent(event);
    }
  }

  private timestamp(): string {
    return new Date().toISOString();
  }

  // ==================== Event Generators ====================

  private jobStarted(): JobStartedEvent {
    return {
      type: 'job_started',
      timestamp: this.timestamp(),
      payload: {
        report_id: this.reportId,
        company_name: this.companyName,
        estimated_duration_seconds: 2400,
      },
    };
  }

  private agentStarted(agentId: AgentType, name: string, desc: string): AgentStartedEvent {
    return {
      type: 'agent_started',
      timestamp: this.timestamp(),
      payload: {
        agent_id: agentId,
        agent_name: name,
        agent_description: desc,
      },
    };
  }

  private agentProgress(agentId: AgentType, progress: number, message: string): AgentProgressEvent {
    return {
      type: 'agent_progress',
      timestamp: this.timestamp(),
      payload: { agent_id: agentId, progress, message },
    };
  }

  private agentCompleted(agentId: AgentType, duration: number, findings: string[]): AgentCompletedEvent {
    return {
      type: 'agent_completed',
      timestamp: this.timestamp(),
      payload: {
        agent_id: agentId,
        duration_seconds: duration,
        summary: {
          records_found: findings.length,
          key_findings: findings,
        },
      },
    };
  }

  private councilStarted(): CouncilStartedEvent {
    return {
      type: 'council_started',
      timestamp: this.timestamp(),
      payload: {
        estimated_duration_seconds: 2100,
        members: MOCK_COUNCIL_MEMBERS,
      },
    };
  }

  private councilPhaseChanged(phase: string, num: number, title: string): CouncilPhaseChangedEvent {
    return {
      type: 'council_phase_changed',
      timestamp: this.timestamp(),
      payload: {
        phase: phase as 'opening' | 'presentation' | 'discussion' | 'decision',
        phase_number: num,
        total_phases: 8,
        phase_title: title,
      },
    };
  }

  private councilSpeakerChanged(memberId: string): CouncilSpeakerChangedEvent {
    const member = MOCK_COUNCIL_MEMBERS.find(m => m.id === memberId)!;
    return {
      type: 'council_speaker_changed',
      timestamp: this.timestamp(),
      payload: {
        speaker_id: member.id,
        speaker_name: member.name,
        speaker_role: member.role,
        speaker_emoji: member.emoji,
      },
    };
  }

  private councilSpeech(
    speakerId: string, 
    chunk: string, 
    isComplete: boolean, 
    riskScore?: number
  ): CouncilSpeechEvent {
    return {
      type: 'council_speech',
      timestamp: this.timestamp(),
      payload: {
        speaker_id: speakerId as 'risk_analyst' | 'business_analyst' | 'legal_expert' | 'media_analyst' | 'sector_expert' | 'moderator',
        chunk,
        is_complete: isComplete,
        risk_score: riskScore,
      },
    };
  }

  private councilScoreRevision(): CouncilScoreRevisionEvent {
    return {
      type: 'council_score_revision',
      timestamp: this.timestamp(),
      payload: {
        speaker_id: 'risk_analyst',
        speaker_name: 'Mehmet Bey',
        old_score: 65,
        new_score: 45,
        reason: 'Tartışmada ortaya çıkan yeni bilgiler ışığında revize ediyorum',
      },
    };
  }

  private councilDecision(): CouncilDecisionEvent {
    return {
      type: 'council_decision',
      timestamp: this.timestamp(),
      payload: {
        final_score: 33,
        risk_level: 'orta_dusuk',
        decision: 'sartli_onay',
        consensus: 0.85,
        conditions: [
          '6 aylık izleme periyodu',
          'Yönetim değişikliği bildirim yükümlülüğü',
          'Çeyreklik finansal rapor talebi',
        ],
        dissent_note: 'Risk analisti başlangıçta yüksek risk görmüş (65), tartışma sonunda revize etmiştir (45).',
        final_scores: {
          risk_analyst: 45,
          business_analyst: 25,
          legal_expert: 30,
          media_analyst: 30,
          sector_expert: 35,
        },
      },
    };
  }

  private jobCompleted(): JobCompletedEvent {
    return {
      type: 'job_completed',
      timestamp: this.timestamp(),
      payload: {
        report_id: this.reportId,
        duration_seconds: 2280,
        final_score: 33,
        risk_level: 'orta_dusuk',
        decision: 'sartli_onay',
      },
    };
  }

  // ==================== Simulation Flow ====================

  async start(): Promise<void> {
    this.isRunning = true;
    this.abortController = new AbortController();
    
    this.options.onOpen?.();

    try {
      // Job Started
      await this.wait(500);
      this.emit(this.jobStarted());

      // Agent Phase
      await this.runAgentPhase();

      // Council Phase
      await this.runCouncilPhase();

      // Job Completed
      await this.wait(500);
      this.emit(this.jobCompleted());

    } catch {
      if (this.isRunning) {
        this.options.onError?.('Simulation error');
      }
    } finally {
      this.close();
    }
  }

  private async runAgentPhase(): Promise<void> {
    // Agent'lar paralel başlar
    await this.wait(100);
    this.emit(this.agentStarted('tsg_agent', 'TSG Agent', 'Ticaret Sicili Gazetesi taranıyor'));
    await this.wait(50);
    this.emit(this.agentStarted('ihale_agent', 'İhale Agent', 'EKAP kayıtları kontrol ediliyor'));
    await this.wait(50);
    this.emit(this.agentStarted('news_agent', 'News Agent', 'Haberler analiz ediliyor'));

    // İhale agent en hızlı biter
    await this.wait(1000);
    this.emit(this.agentProgress('ihale_agent', 50, 'EKAP sorgulanıyor...'));
    await this.wait(800);
    this.emit(this.agentCompleted('ihale_agent', 45, ['İhale yasağı bulunmuyor']));

    // TSG progress
    await this.wait(500);
    this.emit(this.agentProgress('tsg_agent', 25, '2/8 PDF analiz edildi'));
    await this.wait(800);
    this.emit(this.agentProgress('tsg_agent', 50, '4/8 PDF analiz edildi'));

    // News progress
    await this.wait(500);
    this.emit(this.agentProgress('news_agent', 40, '10/24 haber analiz edildi'));
    await this.wait(800);
    this.emit(this.agentProgress('news_agent', 80, '20/24 haber analiz edildi'));

    // News biter
    await this.wait(600);
    this.emit(this.agentCompleted('news_agent', 120, [
      '24 haber bulundu',
      'Sentiment: %62 pozitif',
    ]));

    // TSG biter
    await this.wait(400);
    this.emit(this.agentProgress('tsg_agent', 75, '6/8 PDF analiz edildi'));
    await this.wait(600);
    this.emit(this.agentProgress('tsg_agent', 100, '8/8 PDF analiz edildi'));
    await this.wait(300);
    this.emit(this.agentCompleted('tsg_agent', 180, [
      'Sermaye artışı tespit edildi',
      '3 yönetici değişikliği bulundu',
    ]));
  }

  private async runCouncilPhase(): Promise<void> {
    await this.wait(500);
    this.emit(this.councilStarted());

    // Transcript'ten konuşmaları simüle et
    let lastPhase = '';
    let phaseNum = 0;

    for (const entry of MOCK_TRANSCRIPT) {
      if (!this.isRunning) break;

      // Faz değişimi
      if (entry.phase !== lastPhase) {
        phaseNum++;
        const phaseTitle = this.getPhaseTitleForEntry(entry.phase, entry.speaker_id);
        this.emit(this.councilPhaseChanged(entry.phase, phaseNum, phaseTitle));
        lastPhase = entry.phase;
        await this.wait(300);
      }

      // Konuşmacı değişimi
      this.emit(this.councilSpeakerChanged(entry.speaker_id));
      await this.wait(200);

      // Konuşmayı chunk'lara böl ve streaming simüle et
      const words = entry.content.split(' ');
      const chunkSize = 5; // 5 kelimelik chunk'lar
      
      for (let i = 0; i < words.length; i += chunkSize) {
        if (!this.isRunning) break;
        
        const chunk = words.slice(i, i + chunkSize).join(' ');
        const isLast = i + chunkSize >= words.length;
        
        this.emit(this.councilSpeech(
          entry.speaker_id,
          chunk + (isLast ? '' : ' '),
          isLast,
          isLast ? (entry.risk_score ?? undefined) : undefined
        ));
        
        await this.wait(150);
      }

      await this.wait(500);

      // Tartışma fazında skor revizyonu
      if (entry.phase === 'discussion' && entry.speaker_id === 'risk_analyst' && entry.content.includes('revize')) {
        await this.wait(300);
        this.emit(this.councilScoreRevision());
        await this.wait(500);
      }
    }

    // Final karar
    await this.wait(300);
    this.emit(this.councilDecision());
  }

  private getPhaseTitleForEntry(phase: string, speakerId: string): string {
    if (phase === 'opening') return 'Açılış';
    if (phase === 'discussion') return 'Tartışma';
    if (phase === 'decision') return 'Final Karar';
    
    // Presentation - konuşmacıya göre
    const titles: Record<string, string> = {
      risk_analyst: 'Risk Analisti Sunumu',
      business_analyst: 'İş Analisti Sunumu',
      legal_expert: 'Hukuk Uzmanı Sunumu',
      media_analyst: 'İtibar Analisti Sunumu',
      sector_expert: 'Sektör Uzmanı Sunumu',
    };
    return titles[speakerId] || 'Sunum';
  }

  close(): void {
    this.isRunning = false;
    this.abortController?.abort();
    this.options.onClose?.();
  }
}

// ==================== Factory Function ====================

export function createMockWebSocket(
  reportId: string,
  companyName: string,
  options: MockWebSocketOptions
): MockWebSocket {
  return new MockWebSocket(reportId, companyName, options);
}
