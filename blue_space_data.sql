-- PCAP Entries for Blue Space
INSERT INTO tbPCAP (lp_short_name, pcap_date, field_num, field, amount) VALUES 
('Blue Space', '2023-12-31', 1, 'Initial Capital Balance', 1000000),
('Blue Space', '2023-12-31', 2, 'Capital Calls', 250000),
('Blue Space', '2023-12-31', 3, 'Ending Capital Balance', 250000),
('Blue Space', '2024-03-31', 2, 'Capital Calls', 150000),
('Blue Space', '2024-03-31', 4, 'Reinvested Amount', 50000),
('Blue Space', '2024-03-31', 3, 'Ending Capital Balance', 450000),
('Blue Space', '2024-06-30', 2, 'Capital Calls', 100000),
('Blue Space', '2024-06-30', 4, 'Reinvested Amount', 75000),
('Blue Space', '2024-06-30', 3, 'Ending Capital Balance', 625000);

-- Ledger Entries for Blue Space
INSERT INTO tbLedger (entry_date, activity_date, effective_date, activity, sub_activity, amount, entity_from, entity_to, related_entity, related_fund) VALUES
('2023-10-15', '2023-10-15', '2023-10-15', 'Capital Call', 'Initial', 250000, 'Blue Space', 'ABF24', 'Blue Space', 'ABF24'),
('2023-12-20', '2023-12-20', '2023-12-20', 'LP Distribution', 'Income', 15000, 'ABF24', 'Blue Space', 'Blue Space', 'ABF24'),
('2024-02-10', '2024-02-10', '2024-02-10', 'Capital Call', 'Subsequent', 150000, 'Blue Space', 'ABF24', 'Blue Space', 'ABF24'),
('2024-03-15', '2024-03-15', '2024-03-15', 'LP Distribution', 'Income', 30000, 'ABF24', 'Blue Space', 'Blue Space', 'ABF24'),
('2024-03-15', '2024-03-15', '2024-03-15', 'Reinvestment', 'Income Reinvestment', 50000, 'Blue Space', 'ABF24', 'Blue Space', 'ABF24'),
('2024-05-20', '2024-05-20', '2024-05-20', 'Capital Call', 'Subsequent', 100000, 'Blue Space', 'ABF24', 'Blue Space', 'ABF24'),
('2024-06-15', '2024-06-15', '2024-06-15', 'LP Distribution', 'Income', 45000, 'ABF24', 'Blue Space', 'Blue Space', 'ABF24'),
('2024-06-15', '2024-06-15', '2024-06-15', 'Reinvestment', 'Income Reinvestment', 75000, 'Blue Space', 'ABF24', 'Blue Space', 'ABF24');
