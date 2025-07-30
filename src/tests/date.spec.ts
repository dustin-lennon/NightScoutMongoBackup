import {
	validateDateFormat,
	validateDate,
	parseValidatedDate
} from "#lib/util/date";
import { CommandInteraction } from "discord.js";
import { mockDeep } from "jest-mock-extended";

describe('Date Utilities', () => {
	describe('validateDateFormat', () => {
		it('should return the date string for valid YYYY-MM-DD format', () => {
			expect(validateDateFormat('2022-01-01')).toBe('2022-01-01');
			expect(validateDateFormat('2023-12-31')).toBe('2023-12-31');
			expect(validateDateFormat('1999-06-15')).toBe('1999-06-15');
		});

		it('should return null for invalid date formats', () => {
			expect(validateDateFormat('2022-1-1')).toBeNull();
			expect(validateDateFormat('22-01-01')).toBeNull();
			expect(validateDateFormat('2022/01/01')).toBeNull();
			expect(validateDateFormat('not-a-date')).toBeNull();
			expect(validateDateFormat('')).toBeNull();
		});
	});

	describe('validateDate', () => {
		it('should return true for valid dates', () => {
			expect(validateDate('2022-01-01')).toBe(true);
			expect(validateDate('2023-12-31')).toBe(true);
			expect(validateDate('2000-02-29')).toBe(true); // Valid leap year
			expect(validateDate('1999-06-15')).toBe(true);
		});

		it('should return false for invalid dates', () => {
			expect(validateDate('2022-13-01')).toBe(false); // Invalid month
			expect(validateDate('2022-01-32')).toBe(false); // Invalid day
			expect(validateDate('2021-02-29')).toBe(false); // Invalid leap year
			expect(validateDate('2022-04-31')).toBe(false); // April has only 30 days
			expect(validateDate('not-a-date')).toBe(false);
		});
	});

	describe('parseValidatedDate', () => {
		let mockInteraction: any;

		beforeEach(() => {
			mockInteraction = mockDeep<CommandInteraction>();
			mockInteraction.editReply.mockResolvedValue({} as any);
		});

		it('should return ISO string for valid date in iso mode', () => {
			const result = parseValidatedDate('2022-01-01', mockInteraction, 'iso');
			expect(typeof result).toBe('string');
			expect(result).toMatch(/2022-01-01T00:00:00\.000/); // Match the date portion, timezone may vary
		});

		it('should return milliseconds for valid date in millis mode', () => {
			const result = parseValidatedDate('2022-01-01', mockInteraction, 'millis');
			expect(typeof result).toBe('number');
			expect(result).toBeGreaterThan(1640000000000); // Should be around Jan 1, 2022
			expect(result).toBeLessThan(1642000000000); // Should be before Feb 1, 2022
		});

		it('should handle different valid dates correctly in iso mode', () => {
			const result = parseValidatedDate('2023-06-15', mockInteraction, 'iso');
			expect(typeof result).toBe('string');
			expect(result).toMatch(/2023-06-15T00:00:00\.000/); // Match the date portion
		});

		it('should handle different valid dates correctly in millis mode', () => {
			const result = parseValidatedDate('2023-06-15', mockInteraction, 'millis');
			expect(typeof result).toBe('number');
			expect(result).toBeGreaterThan(1686700000000); // Should be around June 15, 2023
			expect(result).toBeLessThan(1686900000000); // Should be before June 17, 2023
		});

		it('should return editReply promise for invalid date format', async () => {
			const result = parseValidatedDate('2022-1-1', mockInteraction, 'iso');

			// Should return a promise (from interaction.editReply)
			expect(result).toBeInstanceOf(Promise);

			// Verify the interaction was called with correct error message
			expect(mockInteraction.editReply).toHaveBeenCalledWith('❌ Please enter date in the format of YYYY-MM-DD');
		});

		it('should return editReply promise for invalid date', async () => {
			const result = parseValidatedDate('2022-13-01', mockInteraction, 'millis');

			// Should return a promise (from interaction.editReply)
			expect(result).toBeInstanceOf(Promise);

			// Verify the interaction was called with correct error message
			expect(mockInteraction.editReply).toHaveBeenCalledWith('❌ Not a valid date');
		});

		it('should return editReply promise for non-existent date', async () => {
			const result = parseValidatedDate('2021-02-29', mockInteraction, 'iso');

			// Should return a promise (from interaction.editReply)
			expect(result).toBeInstanceOf(Promise);

			// Verify the interaction was called with correct error message
			expect(mockInteraction.editReply).toHaveBeenCalledWith('❌ Not a valid date');
		});

		it('should handle leap year correctly', () => {
			const result = parseValidatedDate('2020-02-29', mockInteraction, 'millis');
			expect(typeof result).toBe('number');
			expect(result).toBeGreaterThan(1582900000000); // Should be around Feb 29, 2020
			expect(result).toBeLessThan(1583000000000); // Should be before March 1, 2020
		});
	});
});
