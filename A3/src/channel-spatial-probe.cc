// Channel-level readiness check for A3/A4; not a finished paper reproduction.
// Uses ns-3.48 ThreeGppChannelModel and its cluster-centre Doppler convention.
#include "ns3/core-module.h"
#include "ns3/node-container.h"
#include "ns3/constant-position-mobility-model.h"
#include "ns3/constant-velocity-mobility-model.h"
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
constexpr double PI = 3.14159265358979323846;
constexpr double LIGHT_SPEED = 3e8; // same convention as ns-3 channel Doppler

int main(int argc, char** argv)
{
    uint32_t seed = 20261109, run = 1, rows = 4, columns = 25;
    uint32_t tones = 100, samples = 257;
    double frequency = 3.7e9, step = 0.001, speed = 0.1, toneSpacing = 180e3;
    bool nlos = false;
    std::string output = "channel-spatial-probe.csv";
    CommandLine cmd(__FILE__);
    cmd.AddValue("seed", "RngSeedManager seed", seed);
    cmd.AddValue("run", "RngSeedManager run", run);
    cmd.AddValue("rows", "BS array rows", rows);
    cmd.AddValue("columns", "BS array columns", columns);
    cmd.AddValue("tones", "Number of sampled frequency points", tones);
    cmd.AddValue("samples", "Number of trajectory samples", samples);
    cmd.AddValue("frequency", "Carrier frequency in Hz", frequency);
    cmd.AddValue("step", "UE sampling displacement in metres", step);
    cmd.AddValue("speed", "UE speed in metres/second", speed);
    cmd.AddValue("toneSpacing", "Pilot-frequency spacing in Hz", toneSpacing);
    cmd.AddValue("nlos", "Force NLOS instead of LOS", nlos);
    cmd.AddValue("output", "Correlation CSV path", output);
    cmd.Parse(argc, argv);
    NS_ABORT_MSG_IF(rows == 0 || columns == 0 || rows * columns > 255 || tones < 2 || samples < 2 ||
                        frequency <= 0 || step <= 0 || speed <= 0 || toneSpacing <= 0,
                    "Positive scales required; samples/tones >= 2; 1..255 BS elements");
    RngSeedManager::SetSeed(seed);
    RngSeedManager::SetRun(run);

    NodeContainer nodes;
    nodes.Create(2); // UE transmitter first; BS receiver second
    auto ue = CreateObject<ConstantVelocityMobilityModel>();
    ue->SetPosition(Vector(2.0, 2.0, 1.73));
    ue->SetVelocity(Vector(speed, 0, 0));
    auto bs = CreateObject<ConstantPositionMobilityModel>();
    bs->SetPosition(Vector(0, 0, 2.5)); // project assumption, not paper geometry
    nodes.Get(0)->AggregateObject(ue);
    nodes.Get(1)->AggregateObject(bs);

    Ptr<ChannelConditionModel> condition;
    if (nlos)
        condition = CreateObject<NeverLosChannelConditionModel>();
    else
        condition = CreateObject<AlwaysLosChannelConditionModel>();
    auto model = CreateObject<ThreeGppChannelModel>();
    model->SetAttribute("Frequency", DoubleValue(frequency));
    model->SetAttribute("Scenario", StringValue("InH-OfficeMixed"));
    model->SetAttribute("ChannelConditionModel", PointerValue(condition));
    // Updates occur on evaluation after the period has elapsed; evaluate every 10 ms.
    model->SetAttribute("UpdatePeriod", TimeValue(Seconds(0.5 * step / speed)));
    model->AssignStreams(1);
    auto tx = CreateObjectWithAttributes<UniformPlanarArray>(
        "NumRows", UintegerValue(1), "NumColumns", UintegerValue(1),
        "AntennaElement", PointerValue(CreateObject<IsotropicAntennaModel>()));
    auto rx = CreateObjectWithAttributes<UniformPlanarArray>(
        "NumRows", UintegerValue(rows), "NumColumns", UintegerValue(columns),
        "NumVerticalPorts", UintegerValue(rows), "NumHorizontalPorts", UintegerValue(columns),
        "AntennaElement", PointerValue(CreateObject<ThreeGppAntennaModel>()));

    // One mathematical port per element exposes raw antenna channels for an
    // independent cross-check against ns-3's spectrum conversion. This is not
    // a claim of 100 standardized NR SRS antenna ports.
    PhasedArrayModel::ComplexVector txWeights(1);
    txWeights[0] = 1;
    tx->SetBeamformingVector(txWeights);
    PhasedArrayModel::ComplexVector rxWeights(rows * columns);
    for (uint32_t antenna = 0; antenna < rows * columns; ++antenna)
        rxWeights[antenna] = 1;
    rx->SetBeamformingVector(rxWeights);
    std::vector<double> frequencies;
    for (uint32_t tone = 0; tone < tones; ++tone)
        frequencies.push_back(frequency + (static_cast<double>(tone) - (tones - 1) / 2.0) * toneSpacing);
    auto spectrumModel = Create<SpectrumModel>(frequencies);
    auto signal = Create<SpectrumSignalParameters>();
    signal->psd = Create<SpectrumValue>(spectrumModel);
    *signal->psd = 1.0;
    auto spectrum = CreateObject<ThreeGppSpectrumPropagationLossModel>();
    spectrum->SetChannelModel(model);
    uint32_t spectrumChecks = 0;

    std::vector<std::vector<Complex>> snapshots;
    snapshots.reserve(samples);
    uint32_t changes = 0;
    Time previousGeneration = Seconds(0);
    std::ofstream witness(output + ".witness.csv");
    if (!witness)
        throw std::runtime_error("Cannot open witness CSV");
    witness << "time_s,x_m,y_m,rx_elements,tones,clusters,h00_real,h00_imag,channel_generation_s\n";
    witness << std::setprecision(17);

    auto sample = [&]() {
        const auto channel = model->GetChannel(ue, bs, tx, rx);
        const auto params = model->GetParams(ue, bs);
        NS_ABORT_MSG_IF(!params, "Channel parameters missing");
        NS_ABORT_MSG_IF(channel->m_nodeIds.first != nodes.Get(0)->GetId(),
                        "Unexpected channel direction");
        const auto& matrix = channel->m_channel;
        const size_t paths = matrix.GetNumPages();
        NS_ABORT_MSG_IF(matrix.GetNumRows() != rows * columns || matrix.GetNumCols() != 1,
                        "Expected BS-elements x one UE-element channel");
        NS_ABORT_MSG_IF(params->m_delay.size() < paths, "Delay/cluster mismatch");
        if (!snapshots.empty() && channel->m_generatedTime != previousGeneration)
            ++changes;
        previousGeneration = channel->m_generatedTime;
        const double time = Simulator::Now().GetSeconds();
        std::vector<Complex> h(rows * columns * tones, Complex(0, 0));
        for (size_t path = 0; path < paths; ++path)
        {
            // Same centre-angle approximation as ThreeGppSpectrumPropagationLossModel.
            const double aod = params->m_angle[MatrixBasedChannelModel::AOD_INDEX][path] * PI / 180;
            const double zod = params->m_angle[MatrixBasedChannelModel::ZOD_INDEX][path] * PI / 180;
            const double phaseDoppler = 2 * PI * frequency / LIGHT_SPEED * time *
                                        speed * std::sin(zod) * std::cos(aod);
            for (uint32_t tone = 0; tone < tones; ++tone)
            {
                const double offset = (static_cast<double>(tone) - (tones - 1) / 2.0) * toneSpacing;
                // ns-3's spectrum implementation uses the absolute sub-band centre
                // frequency in its delay factor, not only a baseband offset.
                const auto phase = std::polar(1.0, phaseDoppler -
                    2 * PI * (frequency + offset) * params->m_delay[path]);
                for (uint32_t antenna = 0; antenna < rows * columns; ++antenna)
                    h[antenna * tones + tone] += matrix(antenna, 0, path) * phase;
            }
        }
        if (snapshots.empty() || snapshots.size() == samples / 2 || snapshots.size() + 1 == samples)
        {
            // This local ns-3 version evolves delays in-place, while its spectrum
            // cache key only checks band/cluster counts and width. Force a fresh
            // delay-factor computation for this independent validation sample.
            params->m_cachedRbWidth = 0.0;
            const auto spectrumResult = spectrum->CalcRxPowerSpectralDensity(signal, ue, bs, tx, rx);
            const auto reference = spectrumResult->spectrumChannelMatrix;
            NS_ABORT_MSG_IF(!reference || reference->GetNumRows() != rows * columns ||
                                reference->GetNumCols() != 1 || reference->GetNumPages() != tones,
                            "Unexpected spectrum-channel dimensions");
            for (uint32_t port = 0; port < rows * columns; ++port)
                for (uint32_t tone = 0; tone < tones; ++tone)
                {
                    const auto antenna = rx->ArrayIndexFromPortIndex(port, 0);
                    const auto value = h[antenna * tones + tone];
                    NS_ABORT_MSG_IF(std::abs(value - (*reference)(port, 0, tone)) >
                                        1e-9 * std::max(1.0, std::abs(value)),
                                    "Exporter disagrees with ns-3 spectrum conversion");
                }
            ++spectrumChecks;
        }
        double energy = 0;
        for (const auto& value : h)
        {
            NS_ABORT_MSG_IF(!std::isfinite(value.real()) || !std::isfinite(value.imag()),
                            "Non-finite complex channel coefficient");
            energy += std::norm(value);
        }
        NS_ABORT_MSG_IF(energy <= 0, "Zero-energy channel");
        const auto position = ue->GetPosition();
        witness << time << ',' << position.x << ',' << position.y << ',' << rows * columns
                << ',' << tones << ',' << paths << ',' << h[0].real() << ',' << h[0].imag()
                << ',' << channel->m_generatedTime.GetSeconds() << '\n';
        // Normalize each snapshot, as in Eq. 11's pairwise normalization.
        for (auto& value : h)
            value /= std::sqrt(energy);
        snapshots.push_back(std::move(h));
    };
    for (uint32_t index = 0; index < samples; ++index)
        Simulator::Schedule(Seconds(index * step / speed), sample);
    Simulator::Run();
    witness.close();

    std::ofstream csv(output);
    if (!csv)
        throw std::runtime_error("Cannot open correlation CSV");
    csv << "seed,run,nlos,lag_samples,distance_m,distance_lambda,pairs,rho_real,rho_imag,abs_rho\n";
    csv << std::setprecision(17);
    const double wavelength = LIGHT_SPEED / frequency;
    const auto maxLag = std::min(samples - 1, static_cast<uint32_t>(std::floor(2 * wavelength / step)));
    for (uint32_t lag = 0; lag <= maxLag; ++lag)
    {
        Complex sum = 0;
        for (size_t index = 0; index + lag < snapshots.size(); ++index)
            for (size_t k = 0; k < snapshots[index].size(); ++k)
                sum += std::conj(snapshots[index][k]) * snapshots[index + lag][k];
        const auto pairs = snapshots.size() - lag;
        const auto rho = sum / static_cast<double>(pairs);
        NS_ABORT_MSG_IF(std::abs(rho) > 1 + 1e-10, "Correlation magnitude exceeds one");
        csv << seed << ',' << run << ',' << nlos << ',' << lag << ',' << lag * step << ','
            << lag * step / wavelength << ',' << pairs << ',' << rho.real() << ','
            << rho.imag() << ',' << std::abs(rho) << '\n';
    }
    std::cout << "samples=" << snapshots.size() << " rx_elements=" << rows * columns
              << " tones=" << tones << " generation_changes=" << changes
              << " spectrum_cross_checks=" << spectrumChecks
              << " simulated_seconds=" << (samples - 1) * step / speed
              << " output=" << output << '\n';
    Simulator::Destroy();
    return 0;
}
