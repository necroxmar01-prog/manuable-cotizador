import { FormControl } from '@angular/forms';

import {
  emailFormatValidator,
  positiveDecimalValidator,
  postalCodeValidator,
  sanitizeEmail,
  sanitizePostalCode,
  sanitizeWeight,
  alphanumericAtValidator,
  sanitizeAlphanumericAt,
  containsLetters,
  sanitizeDimension,
  dimensionValidator
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
    describe('Usuario y contraseña', () => {
    it('debe conservar únicamente letras sin acentos, números y arroba', () => {
      expect(sanitizeAlphanumericAt('Admin123@')).toBe('Admin123@');
      expect(sanitizeAlphanumericAt('José #admin-01.test')).toBe('Josadmin01test');
    });

    it('debe preservar mayúsculas y minúsculas', () => {
      expect(sanitizeAlphanumericAt('AdminABC')).toBe('AdminABC');
      expect(sanitizeAlphanumericAt('A1@z')).toBe('A1@z');
    });

    it('debe aceptar valores con caracteres permitidos', () => {
      expect(
        alphanumericAtValidator(new FormControl('Admin123@'))
      ).toBeNull();
    });

    it('debe aceptar valores vacíos para que required los controle por separado', () => {
      expect(
        alphanumericAtValidator(new FormControl(''))
      ).toBeNull();
    });

    it('debe rechazar acentos, espacios y caracteres especiales no permitidos', () => {
      const invalidValues = [
        'José',
        'usuario nombre',
        'user#123',
        'user-123',
        'user.test',
        'user/123'
      ];

      invalidValues.forEach(value => {
        expect(
          alphanumericAtValidator(new FormControl(value))
        ).not.toBeNull();
      });
    });
  });
});

describe('Reglas de fase 2', () => {
  it('quita espacios pegados alrededor del código postal', () => {
    expect(sanitizePostalCode(' 06600 ')).toBe('06600');
    expect(sanitizePostalCode('06 600')).toBe('06600');
  });

  it('detecta cuando escriben una ciudad en lugar del código postal', () => {
    expect(containsLetters('Monterrey')).toBe(true);
    expect(containsLetters('Ciudad de México')).toBe(true);
    expect(containsLetters('06600 ')).toBe(false);
  });

  it('limita medidas a dos decimales y 300 cm', () => {
    expect(sanitizeDimension('40.555')).toBe('40.55');
    expect(sanitizeDimension('3001')).toBe('300');
    expect(sanitizeDimension('-5')).toBe('');
  });

  it('valida medidas positivas', () => {
    expect(dimensionValidator(new FormControl('40'))).toBeNull();
    expect(dimensionValidator(new FormControl('0'))).toEqual({ invalidDimension: true });
    expect(dimensionValidator(new FormControl('301'))).toEqual({ invalidDimension: true });
  });
});
