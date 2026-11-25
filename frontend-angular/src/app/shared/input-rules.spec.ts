import { FormControl } from '@angular/forms';

import {
  emailFormatValidator,
  positiveDecimalValidator,
  postalCodeValidator,
  sanitizeEmail,
  sanitizePostalCode,
  sanitizeWeight
} from './input-rules';

describe('Reglas reutilizables de entradas', () => {
  describe('Código postal', () => {
    it('debe conservar únicamente cinco dígitos', () => {
      expect(sanitizePostalCode('ABC64000123')).toBe('64000');
    });

    it('debe aceptar exactamente cinco dígitos', () => {
      expect(postalCodeValidator(new FormControl('64000'))).toBeNull();
    });

    it('debe rechazar códigos postales incompletos', () => {
      expect(postalCodeValidator(new FormControl('6400'))).toEqual({
        invalidPostalCode: true
      });
    });
  });

  describe('Peso', () => {
    it('debe limitar los decimales a tres', () => {
      expect(sanitizeWeight('2.56789')).toBe('2.567');
    });

    it('debe conservar un solo punto decimal', () => {
      expect(sanitizeWeight('2..5')).toBe('2.5');
    });

    it('no debe convertir un peso negativo en positivo', () => {
      expect(sanitizeWeight('-5')).toBe('');
    });

    it('debe rechazar pesos superiores a 1000 kg durante la sanitización', () => {
      expect(sanitizeWeight('1000.001')).toBe('');
      expect(sanitizeWeight('23213123123123123123123123123123123123')).toBe('');
    });

    it('debe rechazar entradas excesivamente largas', () => {
      expect(sanitizeWeight('123456789')).toBe('');
    });

    it('debe aceptar pesos positivos de hasta tres decimales', () => {
      expect(positiveDecimalValidator(new FormControl('2.567'))).toBeNull();
      expect(positiveDecimalValidator(new FormControl('1000'))).toBeNull();
    });

    it('debe rechazar cero, negativos y pesos mayores al límite', () => {
      expect(positiveDecimalValidator(new FormControl('0'))).not.toBeNull();
      expect(positiveDecimalValidator(new FormControl('-5'))).not.toBeNull();
      expect(positiveDecimalValidator(new FormControl('1000.001'))).not.toBeNull();
    });
  });

  describe('Correo electrónico', () => {
    it('debe eliminar caracteres no permitidos', () => {
      expect(sanitizeEmail('José/test@gmail.com')).toBe('jostest@gmail.com');
    });

    it('debe convertir las mayúsculas a minúsculas', () => {
      expect(sanitizeEmail('Usuario@GMAIL.COM')).toBe('usuario@gmail.com');
    });

    it('debe aceptar un correo con formato válido en minúsculas', () => {
      expect(emailFormatValidator(new FormControl('usuario@gmail.com'))).toBeNull();
    });

    it('debe rechazar mayúsculas si llegan directamente al validador', () => {
      expect(emailFormatValidator(new FormControl('Usuario@gmail.com'))).not.toBeNull();
    });

    it('debe rechazar acentos y diagonales si llegan directamente al validador', () => {
      expect(emailFormatValidator(new FormControl('José@gmail.com'))).not.toBeNull();
      expect(emailFormatValidator(new FormControl('Jose/test@gmail.com'))).not.toBeNull();
    });
  });
});
