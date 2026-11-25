
import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

import { QuoteOption } from './quote.service';

export interface LeadQuote {
  id: number;
  origin_postal_code: string;
  destination_postal_code: string;
  weight_kg: number | string;
  distance_km: number | string;
  zone: number;
  created_at: string;
  options: QuoteOption[];
}

export interface Lead {
  id: number;
  email: string;
  created_at: string;
  quotes: LeadQuote[];
}

export interface LeadListResponse {
  items: Lead[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

@Injectable({
  providedIn: 'root'
})
export class AdminService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = 'http://localhost:8000/api/leads';

  getLeads(
    username: string,
    password: string,
    page = 1,
    pageSize = 20
  ): Observable<LeadListResponse> {
    const authorization = btoa(`${username}:${password}`);

    const headers = new HttpHeaders({
      Authorization: `Basic ${authorization}`
    });

    const params = new HttpParams()
      .set('page', page)
      .set('page_size', pageSize);

    return this.http.get<LeadListResponse>(this.apiUrl, {
      headers,
      params
    });
  }
}