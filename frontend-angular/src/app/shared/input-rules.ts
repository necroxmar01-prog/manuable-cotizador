import {
  AbstractControl,
  ValidationErrors
} from '@angular/forms';

export function postalCodeValidator(
  control: AbstractControl
): ValidationErrors | null {
  const value = String(control.value ?? '');

  if (!value) return null;

  return /^\d{5}$/.test(value)
    ? null
    : { invalidPostalCode: true };
}

export function positiveDecimalValidator(
  control: AbstractControl
): ValidationErrors | null {
  const value = control.value;

  if (value === null || value === '') return null;

  const text = String(value);

  if (!/^\d+(\.\d{1,3})?$/.test(text)) {
    return { invalidNumber: true };
  }

  const number = Number(text);

  return Number.isFinite(number) && number > 0 && number <= 1000
    ? null
    : { invalidNumber: true };
}

export function sanitizePostalCode(value: string): string {
  return value.replace(/\D/g, '').slice(0, 5);
}

export function sanitizeWeight(value: string): string {
  if (value.includes('-')) return '';

  let sanitized = value.replace(/[^\d.]/g, '');
  const decimalParts = sanitized.split('.');

  if (decimalParts.length > 2) {
    sanitized = decimalParts[0] + '.' + decimalParts.slice(1).join('');
  }

  const parts = sanitized.split('.');

  if (parts.length === 2) {
    sanitized = parts[0] + '.' + parts[1].slice(0, 3);
  }

  if (sanitized.length > 8) return '';

  const number = Number(sanitized);

  if (sanitized !== '' && number > 1000) return '';

  return sanitized;
}

export function sanitizeEmail(value: string): string {
  return value
    .replace(/[^A-Za-z0-9._%+@-]/g, '')
    .toLowerCase();
}

export function emailFormatValidator(
  control: AbstractControl
): ValidationErrors | null {
  const value = String(control.value ?? '');

  if (!value) return null;

  const pattern = /^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$/;

  return pattern.test(value)
    ? null
    : { invalidEmailFormat: true };
}



export function sanitizeAlphanumericAt(value: string): string {
  return value.replace(/[^A-Za-z0-9@]/g, '');
}

export function alphanumericAtValidator(
  control: AbstractControl
): ValidationErrors | null {
  const value = String(control.value ?? '');

  if (!value) return null;

  return /^[A-Za-z0-9@]+$/.test(value)
    ? null
    : { invalidCharacters: true };
}