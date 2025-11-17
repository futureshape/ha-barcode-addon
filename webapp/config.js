// Configuration for Label Printer Application

// Standard leftover options for quick selection
export const STANDARD_LEFTOVERS = [
    'Curry',
    'Stir Fry',
    'Pasta',
    'Rice',
    'Soup',
    'Chili',
    'Fish',
    'Meat'
];

// Standard labels with Material Design Icons and text
// Format: { icon: 'mdi:icon-name', label: 'Display Text' }
export const STANDARD_LABELS = [
    { icon: 'mdi:cow-off', label: 'Lactose Free' },
    { icon: 'mdi:barley-off', label: 'Gluten Free' },
];

// Duration presets for opened ingredients (in days)
export const DURATION_PRESETS = [
    { value: 1, type: 'days', label: '1 Day' },
    { value: 3, type: 'days', label: '3 Days' },
    { value: 5, type: 'days', label: '5 Days' },
    { value: 7, type: 'days', label: '7 Days' },
    { value: 1, type: 'weeks', label: '1 Week' },
    { value: 2, type: 'weeks', label: '2 Weeks' },
    { value: 3, type: 'weeks', label: '3 Weeks' },
    { value: 4, type: 'weeks', label: '4 Weeks' },
];
