#include "ns3/core-module.h"
#include "ns3/node-container.h"
#include "ns3/constant-position-mobility-model.h"
#include "ns3/three-gpp-channel-model.h"
#include "ns3/channel-condition-model.h"
#include "ns3/uniform-planar-array.h"
#include "ns3/isotropic-antenna-model.h"
#include "ns3/three-gpp-antenna-model.h"
#include "ns3/three-gpp-spectrum-propagation-loss-model.h"
#include "ns3/spectrum-signal-parameters.h"
#include "ns3/spectrum-value.h"
#include <algorithm>
#include <cmath>
#include <complex>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>

using namespace ns3;
using Complex = std::complex<double>;

int main(int argc, char** argv)
{
    uint32_t seed = 20261109, run = 1;
    double ueX = 3.19, ueY = .42;
    std::string output = "figure6-channel.csv";
    CommandLine cmd;
    cmd.AddValue("seed", "Channel RNG seed", seed);
    cmd.AddValue("run", "Channel RNG run", run);
    cmd.AddValue("ueX", "Approximate position-A x coordinate in metres", ueX);
    cmd.AddValue("ueY", "Approximate position-A y coordinate in metres", ueY);
    cmd.AddValue("output", "Complex frequency-response CSV", output);
    cmd.Parse(argc, argv);
    NS_ABORT_MSG_IF(!std::isfinite(ueX) || !std::isfinite(ueY), "Invalid UE position");
    RngSeedManager::SetSeed(seed);
    RngSeedManager::SetRun(run);
    NodeContainer nodes;
    nodes.Create(2);
    auto ue = CreateObject<ConstantPositionMobilityModel>();
    auto bs = CreateObject<ConstantPositionMobilityModel>();
    ue->SetPosition(Vector(ueX, ueY, 1.73));
    bs->SetPosition(Vector(0, 0, 2.5));
    nodes.Get(0)->AggregateObject(ue);
    nodes.Get(1)->AggregateObject(bs);
    auto model = CreateObject<ThreeGppChannelModel>();
    model->SetAttribute("Frequency", DoubleValue(3.7e9));
    model->SetAttribute("Scenario", StringValue("InH-OfficeMixed"));
    model->SetAttribute("ChannelConditionModel", PointerValue(CreateObject<AlwaysLosChannelConditionModel>()));
    model->AssignStreams(1);
    auto tx = CreateObjectWithAttributes<UniformPlanarArray>(
        "NumRows", UintegerValue(1), "NumColumns", UintegerValue(1),
        "AntennaElement", PointerValue(CreateObject<IsotropicAntennaModel>()));
    auto rx = CreateObjectWithAttributes<UniformPlanarArray>(
        "NumRows", UintegerValue(4), "NumColumns", UintegerValue(25),
        "NumVerticalPorts", UintegerValue(4), "NumHorizontalPorts", UintegerValue(25),
        "AntennaElement", PointerValue(CreateObject<ThreeGppAntennaModel>()));
    PhasedArrayModel::ComplexVector txWeights(1), rxWeights(100);
    txWeights[0] = 1;
    for (uint32_t a = 0; a < 100; ++a) rxWeights[a] = 1;
    tx->SetBeamformingVector(txWeights);
    rx->SetBeamformingVector(rxWeights);
    std::vector<double> frequencies;
    for (uint32_t k = 0; k < 100; ++k)
        frequencies.push_back(3.7e9 + (static_cast<double>(k) - 49.5) * 180e3);
    auto channel = model->GetChannel(ue, bs, tx, rx);
    auto params = model->GetParams(ue, bs);
    NS_ABORT_MSG_IF(!params || channel->m_channel.GetNumRows() != 100 ||
                    channel->m_channel.GetNumCols() != 1, "Incorrect uplink channel shape");
    const auto paths = channel->m_channel.GetNumPages();
    NS_ABORT_MSG_IF(params->m_delay.size() < paths, "Delay/cluster mismatch");
    std::ofstream csv(output), clusters(output + ".clusters.csv");
    if (!csv || !clusters) throw std::runtime_error("Cannot open output files");
    csv << "antenna,tone,frequency_hz,h_real,h_imag\n" << std::setprecision(17);
    clusters << "antenna,cluster,delay_s,h_real,h_imag\n" << std::setprecision(17);
    std::vector<Complex> h(10000, Complex(0, 0));
    for (uint32_t a = 0; a < 100; ++a)
        for (size_t c = 0; c < paths; ++c)
        {
            const auto coefficient = channel->m_channel(a, 0, c);
            clusters << a + 1 << ',' << c << ',' << params->m_delay[c] << ','
                     << coefficient.real() << ',' << coefficient.imag() << '\n';
            for (uint32_t k = 0; k < 100; ++k)
                h[a * 100 + k] += coefficient *
                    std::polar(1.0, -2 * M_PI * frequencies[k] * params->m_delay[c]);
        }
    auto signal = Create<SpectrumSignalParameters>();
    signal->psd = Create<SpectrumValue>(Create<SpectrumModel>(frequencies));
    *signal->psd = 1.0;
    auto spectrum = CreateObject<ThreeGppSpectrumPropagationLossModel>();
    spectrum->SetChannelModel(model);
    params->m_cachedRbWidth = 0;
    const auto result = spectrum->CalcRxPowerSpectralDensity(signal, ue, bs, tx, rx);
    const auto reference = result->spectrumChannelMatrix;
    NS_ABORT_MSG_IF(!reference || reference->GetNumRows() != 100 ||
                    reference->GetNumCols() != 1 || reference->GetNumPages() != 100,
                    "Incorrect spectrum reference shape");
    double maxError = 0, energy = 0;
    for (uint32_t port = 0; port < 100; ++port)
        for (uint32_t k = 0; k < 100; ++k)
        {
            const auto a = rx->ArrayIndexFromPortIndex(port, 0);
            const auto value = h[a * 100 + k];
            NS_ABORT_MSG_IF(!std::isfinite(value.real()) || !std::isfinite(value.imag()), "Nonfinite channel");
            const auto error = std::abs(value - (*reference)(port, 0, k));
            maxError = std::max(maxError, error);
            NS_ABORT_MSG_IF(error > 1e-9 * std::max(1.0, std::abs(value)), "Spectrum conversion mismatch");
            energy += std::norm(value);
        }
    NS_ABORT_MSG_IF(energy <= 0, "Zero channel energy");
    for (uint32_t a = 0; a < 100; ++a)
        for (uint32_t k = 0; k < 100; ++k)
        {
            const auto value = h[a * 100 + k];
            csv << a + 1 << ',' << k + 1 << ',' << frequencies[k] << ','
                << value.real() << ',' << value.imag() << '\n';
        }
    std::ofstream metadata(output + ".check.json");
    metadata << std::setprecision(17) << "{\"seed\":" << seed << ",\"run\":" << run
             << ",\"antennas\":100,\"tones\":100,\"clusters\":" << paths
             << ",\"spectrum_checks\":1,\"max_spectrum_error\":" << maxError
             << ",\"channel_energy\":" << energy << ",\"time_s\":0}\n";
    std::cout << "PASS static channel: run=" << run << " clusters=" << paths
              << " spectrum_error=" << maxError << " energy=" << energy << '\n';
    Simulator::Destroy();
}
