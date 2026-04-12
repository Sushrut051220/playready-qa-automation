from pathlib import Path

kb = Path("data/kb")

rename_map = {
    "Compliance_Rules_For_PlayReady_Products__1_Nov_2021_1-11_01.pdf": "PR_Compliance_Rules_Part01_v2021.pdf",
    "Compliance_Rules_For_PlayReady_Products__1_Nov_2021_12-29_02.pdf": "PR_Compliance_Rules_Part02_v2021.pdf",
    "Compliance_Rules_For_PlayReady_Products__1_Nov_2021_30-47_03.pdf": "PR_Compliance_Rules_Part03_v2021.pdf",
    "Compliance_Rules_For_PlayReady_Products__1_Nov_2021_48-66_04.pdf": "PR_Compliance_Rules_Part04_v2021.pdf",
    "Compliance_Rules_For_PlayReady_Products__1_Nov_2021_67-end_05.pdf": "PR_Compliance_Rules_Part05_v2021.pdf",
    "DevelopingMicrosoftPlayReadyClients_March2015_1-12_01.pdf": "PR_Dev_Clients_Part01_v2015.pdf",
    "DevelopingMicrosoftPlayReadyClients_March2015_13-end_02.pdf": "PR_Dev_Clients_Part02_v2015.pdf",
    "Instructions For Extended Validation (EV) Certificate.pdf": "PR_EV_Certificate_Instructions.pdf",
    "IPLA Licensing Portal FAQ 3.pdf": "PR_IPLA_Licensing_Portal_FAQ.pdf",
    "Microsoft PlayReady Master Agreement_SAMPLE v-12-04-13a (1).pdf": "PR_Master_Agreement_Sample_v2013.pdf",
    "Microsoft PlayReady Server Agreement v.8.1.2019_SAMPLE (1).pdf": "PR_Server_Agreement_Sample_v2019.pdf",
    "MicrosoftPlayReadyContentProtectionWhitePaper_March2015 (1).pdf": "PR_Content_Protection_Whitepaper_v2015.pdf",
    "PlayReady Development - Microsoft PlayReady (1).pdf": "PR_Development_Overview.pdf",
    "PlayReady Distribution - Microsoft PlayReady (1).pdf": "PR_Distribution_Overview.pdf",
    "playready doc_1-16_01.pdf": "PR_Documentation_Part01.pdf",
    "playready doc_17-32_02.pdf": "PR_Documentation_Part02.pdf",
    "playready doc_33-49_03.pdf": "PR_Documentation_Part03.pdf",
    "playready doc_50-62_04.pdf": "PR_Documentation_Part04.pdf",
    "playready doc_63-73_05.pdf": "PR_Documentation_Part05.pdf",
    "playready doc_74-85_06.pdf": "PR_Documentation_Part06.pdf",
    "playready doc_86-102_07.pdf": "PR_Documentation_Part07.pdf",
    "playready doc_103-121_08.pdf": "PR_Documentation_Part08.pdf",
    "playready doc_122-144_09.pdf": "PR_Documentation_Part09.pdf",
    "playready doc_145-169_10.pdf": "PR_Documentation_Part10.pdf",
    "playready doc_170-185_11.pdf": "PR_Documentation_Part11.pdf",
    "playready doc_186-199_12.pdf": "PR_Documentation_Part12.pdf",
    "playready doc_200-221_13.pdf": "PR_Documentation_Part13.pdf",
    "playready doc_222-254_14.pdf": "PR_Documentation_Part14.pdf",
    "playready doc_255-275_15.pdf": "PR_Documentation_Part15.pdf",
    "playready doc_276-296_16.pdf": "PR_Documentation_Part16.pdf",
    "playready doc_297-end_17.pdf": "PR_Documentation_Part17.pdf",
    "PlayReady Server - Microsoft PlayReady (1).pdf": "PR_Server_Overview.pdf",
    "PlayReady SL3000 Playbook 1.pdf": "PR_SL3000_Playbook.pdf",
    "PR Final Product License v.12.12.2018_SAMPLE (1).pdf": "PR_Final_Product_License_Sample_v2018.pdf",
    "PR Intermediate Product License v.6-02-16a_SAMPLE (1).pdf": "PR_Intermediate_Product_License_Sample_v2016.pdf",
    "ProtectingLiveTVServicesWithPlayReady_March2015_1-20_01.pdf": "PR_LiveTV_Protection_Part01_v2015.pdf",
    "ProtectingLiveTVServicesWithPlayReady_March2015_21-end_02.pdf": "PR_LiveTV_Protection_Part02_v2015.pdf",
}

# Handle What's New files (special characters in filename)
for f in kb.glob("What*New*.pdf"):
    for ver in ["4.2", "4.3", "4.4", "4.5", "4.6"]:
        if ver in f.name:
            rename_map[f.name] = f"PR_WhatsNew_v{ver}.pdf"
            break

renamed = 0
skipped = 0
for old_name, new_name in rename_map.items():
    old_path = kb / old_name
    new_path = kb / new_name
    if old_path.exists():
        old_path.rename(new_path)
        print(f"  OK: {old_name}")
        print(f"   -> {new_name}")
        renamed += 1
    else:
        skipped += 1

total = len(list(kb.glob("*.pdf")))
print(f"\nRenamed: {renamed}")
print(f"Skipped: {skipped}")
print(f"Total PDFs now: {total}")