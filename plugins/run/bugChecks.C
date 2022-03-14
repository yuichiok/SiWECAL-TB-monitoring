void eventsPerDat(TTree *ecal) {
  Int_t run_id_max = ecal->GetMaximum("id_run");
  for (Int_t run = ecal->GetMinimum("id_run"); run <= run_id_max; run++) {
    ecal->Draw(
        TString::Format(
            "event:id_dat >> eventsPerDat_%i(%i, %.1f, %.1f, %i, %.1f, %.1f)",
            run,
            Int_t(ecal->GetMaximum("id_dat") - ecal->GetMinimum("id_dat") + 1),
            ecal->GetMinimum("id_dat") - 0.5, ecal->GetMaximum("id_dat") + 0.5,
            Int_t(ecal->GetMaximum("event") - ecal->GetMinimum("event") + 1),
            ecal->GetMinimum("event") - 0.5, ecal->GetMaximum("event") + 0.5),
        TString::Format("id_run == %i", run), "colz,goff");
  }
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
  file->Write();
  file->Close();
}
