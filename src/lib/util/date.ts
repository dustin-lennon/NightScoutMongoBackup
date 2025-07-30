import { CommandInteraction, Message } from 'discord.js';
import { DateTime } from 'luxon';

const dateFormatRegex = /^\d{4}-\d{2}-\d{2}$/;

export function validateDateFormat(date: string): string | null {
	// check if the string matches the YYYY-MM-DD format
	return dateFormatRegex.test(date) ? date : null;
}

export function validateDate(date: string): boolean {
	// Parse the date using the specified format
	const dt = DateTime.fromFormat(date, 'yyyy-MM-dd');
	return dt.isValid;
}

/**
 * Validates and parses a date string into a Luxon value (ISO or millis).
 * Returns a string or number if valid, otherwise returns a `Promise<Message<boolean>>` to reply to the user.
 */
export function parseValidatedDate(
	dateParam: string,
	interaction: CommandInteraction,
	mode: 'iso' | 'millis'
): string | number | Promise<Message<boolean>> {
	if (!validateDateFormat(dateParam)) {
		return interaction.editReply('❌ Please enter date in the format of YYYY-MM-DD');
	}

	if (!validateDate(dateParam)) {
		return interaction.editReply('❌ Not a valid date');
	}

	const dt = DateTime.fromFormat(dateParam, 'yyyy-LL-dd');
	return mode === 'iso' ? dt.toISO()! : dt.toMillis();
}
