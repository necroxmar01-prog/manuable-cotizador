
import { Routes } from '@angular/router';
import { Quote } from './pages/quote/quote';
import { Admin } from './pages/admin/admin';

export const routes: Routes = [
  {
    path: '',
    redirectTo: 'cotizador',
    pathMatch: 'full'
  },
  {
    path: 'cotizador',
    component: Quote
  },
  {
    path: 'admin',
    component: Admin
  },
  {
    path: '**',
    redirectTo: 'cotizador'
  }
];
