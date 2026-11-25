
import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { DatePipe } from '@angular/common';
import { FormControl, FormsModule } from '@angular/forms';

import {
  alphanumericAtValidator,
  sanitizeAlphanumericAt
} from '../../shared/input-rules';

import {
  AdminService,
  Lead,
  LeadListResponse
} from '../../core/services/admin.service';

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [RouterLink, FormsModule, DatePipe],
  templateUrl: './admin.html',
  styleUrl: './admin.scss'
})
export class Admin {
  private readonly adminService = inject(AdminService);

  username = '';
  password = '';

  leads: Lead[] = [];
  totalLeads = 0;
  totalQuotes = 0;
  quotesWithoutOptions = 0;

  page = 1;
  pageSize = 20;
  totalPages = 0;

  isLoading = false;
  isAuthenticated = false;
  errorMessage = '';

  login(): void {
    if (!this.username.trim() || !this.password) {
      this.errorMessage = 'Ingresa tu usuario y contraseña.';
      return;
    }

    const usernameErrors = alphanumericAtValidator(
      new FormControl(this.username)
    );

    const passwordErrors = alphanumericAtValidator(
      new FormControl(this.password)
    );

    if (usernameErrors || passwordErrors) {
      this.errorMessage =
        'El usuario y la contraseña solo pueden contener letras sin acentos, números y @.';
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';

    this.adminService.getLeads(
      this.username.trim(),
      this.password,
      this.page,
      this.pageSize
    ).subscribe({
      next: (response: LeadListResponse) => {
        this.isAuthenticated = true;
        this.updateDashboard(response);
        this.isLoading = false;
      },
      error: (error: HttpErrorResponse) => {
        this.isLoading = false;

        if (error.status === 401) {
          this.errorMessage = 'Usuario o contraseña incorrectos.';
        } else if (error.status === 503) {
          this.errorMessage = 'La autenticación administrativa no está configurada en el servidor.';
        } else {
          this.errorMessage = 'No fue posible consultar los leads. Verifica que el servidor esté disponible.';
        }
      }
    });
  }

  loadPage(page: number): void {
    if (page < 1 || page > this.totalPages || this.isLoading) {
      return;
    }

    this.page = page;
    this.isLoading = true;
    this.errorMessage = '';

    this.adminService.getLeads(
      this.username.trim(),
      this.password,
      this.page,
      this.pageSize
    ).subscribe({
      next: (response: LeadListResponse) => {
        this.updateDashboard(response);
        this.isLoading = false;
      },
      error: () => {
        this.isLoading = false;
        this.errorMessage = 'No fue posible cargar esta página.';
      }
    });
  }

  logout(): void {
    this.username = '';
    this.password = '';
    this.leads = [];
    this.totalLeads = 0;
    this.totalQuotes = 0;
    this.quotesWithoutOptions = 0;
    this.totalPages = 0;
    this.page = 1;
    this.isAuthenticated = false;
    this.errorMessage = '';
  }

  private updateDashboard(response: LeadListResponse): void {
    this.leads = response.items;
    this.totalLeads = response.total;
    this.totalPages = response.pages;

    this.totalQuotes = this.leads.reduce(
      (total, lead) => total + lead.quotes.length,
      0
    );

    this.quotesWithoutOptions = this.leads.reduce(
      (total, lead) =>
        total + lead.quotes.filter(quote => quote.options.length === 0).length,
      0
    );
  }

  sanitizeUsername(value: string): void {
    this.username = sanitizeAlphanumericAt(value);
  }

  sanitizePassword(value: string): void {
    this.password = sanitizeAlphanumericAt(value);
  }
}
