void eventsPerDat(TTree *ecal) {
  Int_t run_id_max = ecal->GetMaximum("id_run");
  Int_t dat_min = ecal->GetMinimum("id_dat");
  Int_t dat_max = ecal->GetMaximum("id_dat");
  Int_t event_min = ecal->GetMinimum("event");
  Int_t event_max = ecal->GetMaximum("event");
  for (Int_t run = ecal->GetMinimum("id_run"); run <= run_id_max; run++) {
    ecal->Draw(
        TString::Format(
            "event:id_dat >> eventsPerDat_%i(%i, %.1f, %.1f, %i, %.1f, %.1f)",
            run, dat_max - dat_min + 1, dat_min - 0.5, dat_max + 0.5,
            event_max - event_min + 1, event_min - 0.5, event_max + 0.5),
        TString::Format("id_run == %i", run), "goff");
  }
}

void coincidencesPerDat(TTree *ecal) {
  Int_t run_id_max = ecal->GetMaximum("id_run");
  Int_t dat_min = ecal->GetMinimum("id_dat");
  Int_t dat_max = ecal->GetMaximum("id_dat");
  Int_t nhit_slab_min = ecal->GetMinimum("nhit_slab");
  Int_t nhit_slab_max = ecal->GetMaximum("nhit_slab");
  for (Int_t run = ecal->GetMinimum("id_run"); run <= run_id_max; run++) {
    ecal->Draw(TString::Format("id_dat:nhit_slab >> coincidencesPerDat_%i(%i, "
                               "%.1f, %.1f, %i, %.1f, %.1f)",
                               run, nhit_slab_max - nhit_slab_min + 1,
                               nhit_slab_min - 0.5, nhit_slab_max + 0.5,
                               dat_max - dat_min + 1, dat_min - 0.5,
                               dat_max + 0.5),
               TString::Format("id_run == %i", run), "goff");
  }
}

void bcidChecks(TTree *ecal) {
  ecal->Draw("bcid % 4096 >> bcid_no_overflow(4096, -0.5, 4095.5)", "", "goff");
}

void bugChecks(TString buildfile = "build.root",
               TString output = "bugChecks.root") {
  TFile *in_file = TFile::Open(buildfile);
  TTree *ecal = in_file->Get<TTree>("ecal");
  // Let's not copy the whole file over.
  // gSystem->CopyFile(buildfile, output);
  TFile *file = TFile::Open(output, "create");
  file->mkdir("bug_checks");
  file->GetDirectory("bug_checks")->cd();
  eventsPerDat(ecal);
  coincidencesPerDat(ecal);
  bcidChecks(ecal);
  file->Write();
  file->Close();
}
