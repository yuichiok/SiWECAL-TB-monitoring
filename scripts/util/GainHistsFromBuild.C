#include <TH2.h>
#include <vector>

/* id_layer only necessary if you want to split the job for multiprocessing.
Then:

>>> root -q -l -b
"GainHistsFromBuild.C(\"current_build.root\",\"PedestalMIP_0.root\",1,6,0)" and
iterate through 0,.., 14 (or your highest slab id).
>>> hadd PedestalMIP_all_layers.root PedestalMIP_*.root

Reproduces the MIP histogram out of `DecodedSLBAnalysis::NSlabsAnalysis`.
Instead of taking `converted.root` files as input, it is based on `build.root`.
For the base implementation, see:
https://github.com/SiWECAL-TestBeam/SiWECAL-TB-analysis/blob/9aabcc9fa8764636fac6abc0314fe22c4027bad4/SLBperformance/DecodedSLBAnalysis.cc#L166
*/
int GainHistsFromBuild(TString build_path = "current_build.root",
                       TString output_path = "PedestalMIP_all_layers.root",
                       int max_nhit_per_sca = 1, int min_nhit_slab = 6,
                       int id_layer = -1) {
  TFile *tree_file = TFile::Open(build_path);
  if (!tree_file)
    return -1;
  TTree *ecal = tree_file->Get<TTree>("ecal");
  if (!ecal)
    return -1;

  // Only read the necessary branches.
  int max_nhit_len = ecal->GetMaximum("nhit_len");
  int hit_slab[max_nhit_len], hit_chip[max_nhit_len], hit_chan[max_nhit_len];
  int hit_sca[max_nhit_len], hit_isHit[max_nhit_len];
  int hit_adc_high[max_nhit_len], hit_adc_low[max_nhit_len];
  int nhit_len;
  int nhit_slab;
  ecal->SetBranchStatus("*", 0); // disable all branches
  ecal->SetBranchStatus("hit_slab", 1);
  ecal->SetBranchAddress("hit_slab", &hit_slab);
  ecal->SetBranchStatus("hit_chip", 1);
  ecal->SetBranchAddress("hit_chip", &hit_chip);
  ecal->SetBranchStatus("hit_chan", 1);
  ecal->SetBranchAddress("hit_chan", &hit_chan);
  ecal->SetBranchStatus("hit_sca", 1);
  ecal->SetBranchAddress("hit_sca", &hit_sca);
  ecal->SetBranchStatus("hit_isHit", 1);
  ecal->SetBranchAddress("hit_isHit", &hit_isHit);
  ecal->SetBranchStatus("hit_adc_high", 1);
  ecal->SetBranchAddress("hit_adc_high", &hit_adc_high);
  ecal->SetBranchStatus("hit_adc_low", 1);
  ecal->SetBranchAddress("hit_adc_low", &hit_adc_low);
  ecal->SetBranchStatus("nhit_len", 1);
  ecal->SetBranchAddress("nhit_len", &nhit_len);
  ecal->SetBranchStatus("nhit_slab", 1);
  ecal->SetBranchAddress("nhit_slab", &nhit_slab);

  // Construct Histograms: One per sca, channel, chip, layer.
  int n_slabs = ecal->GetMaximum("hit_slab");
  int highest_slab = n_slabs + 1;
  int n_chips = ecal->GetMaximum("hit_chip");
  int n_chans = ecal->GetMaximum("hit_chan");
  int n_scas = ecal->GetMaximum("hit_sca");
  int i_slab_min = ecal->GetMinimum("hit_slab");
  if (id_layer >= 0) {
    if (id_layer > n_slabs)
      return -1;
    i_slab_min = id_layer;
    n_slabs = 1;
  }
  std::vector<std::vector<std::vector<std::vector<TH1F *>>>> ped_lg_sca;
  std::vector<std::vector<std::vector<std::vector<TH1F *>>>> ped_hg_sca;
  std::vector<std::vector<std::vector<std::vector<TH1F *>>>> mip_lg_sca;
  std::vector<std::vector<std::vector<std::vector<TH1F *>>>> mip_hg_sca;
  for (int i_slab = i_slab_min; i_slab < i_slab_min + n_slabs; i_slab++) {
    std::vector<std::vector<std::vector<TH1F *>>> ped_lowtemp_sca_layer;
    std::vector<std::vector<std::vector<TH1F *>>> ped_hightemp_sca_layer;
    std::vector<std::vector<std::vector<TH1F *>>> mip_lowtemp_sca_layer;
    std::vector<std::vector<std::vector<TH1F *>>> mip_hightemp_sca_layer;
    for (int i_chip = ecal->GetMinimum("hit_chip"); i_chip <= n_chips;
         i_chip++) {
      std::vector<std::vector<TH1F *>> ped_lowtemp_sca;
      std::vector<std::vector<TH1F *>> ped_hightemp_sca;
      std::vector<std::vector<TH1F *>> mip_lowtemp_sca;
      std::vector<std::vector<TH1F *>> mip_hightemp_sca;
      for (int i_chan = ecal->GetMinimum("hit_chan"); i_chan <= n_chans;
           i_chan++) {
        printf("\rConstruct Histograms: On layer/chip/channel: %i/%i/%i    ",
               i_slab, i_chip, i_chan);
        fflush(stdout);
        std::vector<TH1F *> ped_lowtemp_sca2;
        std::vector<TH1F *> ped_hightemp_sca2;
        std::vector<TH1F *> mip_lowtemp_sca2;
        std::vector<TH1F *> mip_hightemp_sca2;
        for (int i_sca = ecal->GetMinimum("hit_sca"); i_sca <= n_scas;
             i_sca++) {
          TH1F *ped_lg_sca2 =
              new TH1F(TString::Format("ped_low_layer%i_chip%i_chn%i_sca%i",
                                       i_slab, i_chip, i_chan, i_sca),
                       TString::Format("ped_low_layer%i_chip%i_chn%i_sca%i",
                                       i_slab, i_chip, i_chan, i_sca),
                       400, 100.5, 500.5);
          TH1F *ped_hg_sca2 =
              new TH1F(TString::Format("ped_high_layer%i_chip%i_chn%i_sca%i",
                                       i_slab, i_chip, i_chan, i_sca),
                       TString::Format("ped_high_layer%i_chip%i_chn%i_sca%i",
                                       i_slab, i_chip, i_chan, i_sca),
                       400, 100.5, 500.5);
          TH1F *mip_lg_sca2 =
              new TH1F(TString::Format("mip_low_layer%i_chip%i_chn%i_sca%i",
                                       i_slab, i_chip, i_chan, i_sca),
                       TString::Format("mip_low_layer%i_chip%i_chn%i_sca%i",
                                       i_slab, i_chip, i_chan, i_sca),
                       500, 100.5, 600.5);
          TH1F *mip_hg_sca2 =
              new TH1F(TString::Format("mip_high_layer%i_chip%i_chn%i_sca%i",
                                       i_slab, i_chip, i_chan, i_sca),
                       TString::Format("mip_high_layer%i_chip%i_chn%i_sca%i",
                                       i_slab, i_chip, i_chan, i_sca),
                       500, 100.5, 600.5);
          ped_lowtemp_sca2.push_back(ped_lg_sca2);
          ped_hightemp_sca2.push_back(ped_hg_sca2);
          mip_lowtemp_sca2.push_back(mip_lg_sca2);
          mip_hightemp_sca2.push_back(mip_hg_sca2);
        }
        ped_lowtemp_sca.push_back(ped_lowtemp_sca2);
        ped_hightemp_sca.push_back(ped_hightemp_sca2);
        mip_lowtemp_sca.push_back(mip_lowtemp_sca2);
        mip_hightemp_sca.push_back(mip_hightemp_sca2);
      }
      ped_lowtemp_sca_layer.push_back(ped_lowtemp_sca);
      ped_hightemp_sca_layer.push_back(ped_hightemp_sca);
      mip_lowtemp_sca_layer.push_back(mip_lowtemp_sca);
      mip_hightemp_sca_layer.push_back(mip_hightemp_sca);
    }
    ped_lg_sca.push_back(ped_lowtemp_sca_layer);
    ped_hg_sca.push_back(ped_hightemp_sca_layer);
    mip_lg_sca.push_back(mip_lowtemp_sca_layer);
    mip_hg_sca.push_back(mip_hightemp_sca_layer);
  }
  std::cout << std::endl;

  // Basic Pedestal/MIP analysis
  int nhit_per_sca[highest_slab][n_chips][n_scas];
  int hit_slab_i = 0;
  int i_hits_all = 0;
  int i_hits_enough_slabs = 0;
  int i_hits_correct_layer = 0;
  int i_hits_filled = 0;
  for (Long64_t i_event = 0; i_event < ecal->GetEntries(); i_event++) {
    ecal->GetEntry(i_event);
    i_hits_all = i_hits_all + nhit_len;
    if (nhit_slab < min_nhit_slab) {
      continue;
    }
    i_hits_enough_slabs = i_hits_enough_slabs + nhit_len;
    memset(nhit_per_sca, 0, sizeof(nhit_per_sca));
    for (int i = 0; i < nhit_len; i++) {
      if (hit_isHit[i]) {
        nhit_per_sca[hit_slab[i]][hit_chip[i]][hit_sca[i]]++;
      }
    }
    for (int i = 0; i < nhit_len; i++) {
      if (id_layer < 0) {
        hit_slab_i = hit_slab[i];
      } else if (hit_slab[i] == id_layer) {
        hit_slab_i = 0;
      } else {
        continue;
      }
      i_hits_correct_layer++;
      if (nhit_per_sca[hit_slab[i]][hit_chip[i]][hit_sca[i]] >
          max_nhit_per_sca) {
        continue;
      }
      if (hit_isHit[i]) {
        mip_lg_sca.at(hit_slab_i)
            .at(hit_chip[i])
            .at(hit_chan[i])
            .at(hit_sca[i])
            ->Fill(hit_adc_low[i]);
        mip_hg_sca.at(hit_slab_i)
            .at(hit_chip[i])
            .at(hit_chan[i])
            .at(hit_sca[i])
            ->Fill(hit_adc_high[i]);
        i_hits_filled++;
      } else {
        ped_lg_sca.at(hit_slab_i)
            .at(hit_chip[i])
            .at(hit_chan[i])
            .at(hit_sca[i])
            ->Fill(hit_adc_low[i]);
        ped_hg_sca.at(hit_slab_i)
            .at(hit_chip[i])
            .at(hit_chan[i])
            .at(hit_sca[i])
            ->Fill(hit_adc_high[i]);
      }
    }
  }
  std::cout << "# hits: " << i_hits_all << std::endl;
  std::cout << "# hits on at least " << min_nhit_slab
            << " slabs: " << i_hits_enough_slabs << std::endl;
  std::cout << "# hits on considered layer(s): " << i_hits_correct_layer
            << std::endl;
  std::cout << "# hits filled: " << i_hits_filled << std::endl;

  // Write the histograms
  TFile *gains_file = new TFile(output_path, "RECREATE");
  gains_file->cd();
  TDirectory *layer_dir[i_slab_min + n_slabs];
  for (int i_slab = i_slab_min; i_slab < i_slab_min + n_slabs; i_slab++) {
    layer_dir[i_slab] = gains_file->mkdir(TString::Format("layer_%i", i_slab));
  }

  int i_slab_pos = 0;
  for (int i_slab = i_slab_min; i_slab < i_slab_min + n_slabs; i_slab++) {
    layer_dir[i_slab]->cd();
    if (id_layer < 0) {
      i_slab_pos = i_slab;
    } else {
      i_slab_pos = 0;
    }
    for (int i_chip = ecal->GetMinimum("hit_chip"); i_chip <= n_chips;
         i_chip++) {
      for (int i_chan = ecal->GetMinimum("hit_chan"); i_chan <= n_chans;
           i_chan++) {
        printf("\rWrite Histograms: On layer/chip/channel: %i/%i/%i    ",
               i_slab, i_chip, i_chan);
        fflush(stdout);
        for (int i_sca = ecal->GetMinimum("hit_sca"); i_sca <= n_scas;
             i_sca++) {
          ped_lg_sca.at(i_slab_pos)
              .at(i_chip)
              .at(i_chan)
              .at(i_sca)
              ->SetTitle(TString::Format("ped_low_chip%i_chn%i_sca%i", i_chip,
                                         i_chan, i_sca));
          ped_lg_sca.at(i_slab_pos)
              .at(i_chip)
              .at(i_chan)
              .at(i_sca)
              ->SetName(TString::Format("ped_low_chip%i_chn%i_sca%i", i_chip,
                                        i_chan, i_sca));
          ped_lg_sca.at(i_slab_pos).at(i_chip).at(i_chan).at(i_sca)->Write();
          ped_hg_sca.at(i_slab_pos)
              .at(i_chip)
              .at(i_chan)
              .at(i_sca)
              ->SetTitle(TString::Format("ped_high_chip%i_chn%i_sca%i", i_chip,
                                         i_chan, i_sca));
          ped_hg_sca.at(i_slab_pos)
              .at(i_chip)
              .at(i_chan)
              .at(i_sca)
              ->SetName(TString::Format("ped_high_chip%i_chn%i_sca%i", i_chip,
                                        i_chan, i_sca));
          ped_hg_sca.at(i_slab_pos).at(i_chip).at(i_chan).at(i_sca)->Write();
          mip_lg_sca.at(i_slab_pos)
              .at(i_chip)
              .at(i_chan)
              .at(i_sca)
              ->SetTitle(TString::Format("mip_low_chip%i_chn%i_sca%i", i_chip,
                                         i_chan, i_sca));
          mip_lg_sca.at(i_slab_pos)
              .at(i_chip)
              .at(i_chan)
              .at(i_sca)
              ->SetName(TString::Format("mip_low_chip%i_chn%i_sca%i", i_chip,
                                        i_chan, i_sca));
          mip_lg_sca.at(i_slab_pos).at(i_chip).at(i_chan).at(i_sca)->Write();
          mip_hg_sca.at(i_slab_pos)
              .at(i_chip)
              .at(i_chan)
              .at(i_sca)
              ->SetTitle(TString::Format("mip_high_chip%i_chn%i_sca%i", i_chip,
                                         i_chan, i_sca));
          mip_hg_sca.at(i_slab_pos)
              .at(i_chip)
              .at(i_chan)
              .at(i_sca)
              ->SetName(TString::Format("mip_high_chip%i_chn%i_sca%i", i_chip,
                                        i_chan, i_sca));
          mip_hg_sca.at(i_slab_pos).at(i_chip).at(i_chan).at(i_sca)->Write();
        }
      }
    }
  }
  ped_lg_sca.clear();
  ped_hg_sca.clear();
  mip_lg_sca.clear();
  mip_hg_sca.clear();
  gains_file->Close();
  delete gains_file;
  return 1;
}
