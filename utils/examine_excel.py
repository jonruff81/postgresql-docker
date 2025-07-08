import pandas as pd

# [NOTE] PlanElevOptions is now archived. Update path to archived location.
df = pd.read_excel('../archived/cleanup_2025/PlanElevOptions/Croydonette_B_Basement_Base Home.xlsx')

print('COLUMNS:')
for i, col in enumerate(df.columns):
    print(f'{i+1}: {col}')

print(f'\nTotal rows: {len(df)}')
print('\nFirst row values:')
print(df.iloc[0])
