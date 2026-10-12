/*
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * A deterministic XR pose uplink baseline:
 *   - pose sampling: 1 kHz
 *   - reporting: 100 Hz, latest sample only
 *   - application data: 12-byte report header + 60-byte pose = 72 bytes
 *   - UDP/IPv4 packet: 72 + 8 + 20 = 100 bytes
 *   - point-to-point link: 10 Mbps, 1 ms propagation delay
 */

#include "ns3/core-module.h"
#include "ns3/internet-module.h"
#include "ns3/mobility-module.h"
#include "ns3/network-module.h"
#include "ns3/point-to-point-module.h"

#include <algorithm>
#include <array>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <map>
#include <numeric>
#include <string>
#include <vector>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("XrPoseUplink");

namespace
{

constexpr uint32_t POSE_BYTES = 60;
constexpr uint32_t REPORT_HEADER_BYTES = 12;
constexpr uint32_t UDP_HEADER_BYTES = 8;
constexpr uint32_t IPV4_HEADER_BYTES = 20;
constexpr uint32_t IP_PACKET_BYTES =
    POSE_BYTES + REPORT_HEADER_BYTES + UDP_HEADER_BYTES + IPV4_HEADER_BYTES;

void
WriteFloat(Buffer::Iterator& iterator, float value)
{
    uint32_t bits;
    static_assert(sizeof(bits) == sizeof(value));
    std::memcpy(&bits, &value, sizeof(bits));
    iterator.WriteHtonU32(bits);
}

float
ReadFloat(Buffer::Iterator& iterator)
{
    const uint32_t bits = iterator.ReadNtohU32();
    float value;
    std::memcpy(&value, &bits, sizeof(value));
    return value;
}

class PosePayloadHeader : public Header
{
  public:
    static TypeId GetTypeId()
    {
        static TypeId tid = TypeId("PosePayloadHeader")
                                .SetParent<Header>()
                                .AddConstructor<PosePayloadHeader>();
        return tid;
    }

    TypeId GetInstanceTypeId() const override
    {
        return GetTypeId();
    }

    uint32_t GetSerializedSize() const override
    {
        return POSE_BYTES;
    }

    void Serialize(Buffer::Iterator start) const override
    {
        for (float value : m_position)
        {
            WriteFloat(start, value);
        }
        for (float value : m_orientation)
        {
            WriteFloat(start, value);
        }
        start.WriteHtonU64(m_sampleTimeNs);
        start.WriteHtonU32(m_deviceId);
        for (uint32_t value : m_reserved)
        {
            start.WriteHtonU32(value);
        }
    }

    uint32_t Deserialize(Buffer::Iterator start) override
    {
        for (float& value : m_position)
        {
            value = ReadFloat(start);
        }
        for (float& value : m_orientation)
        {
            value = ReadFloat(start);
        }
        m_sampleTimeNs = start.ReadNtohU64();
        m_deviceId = start.ReadNtohU32();
        for (uint32_t& value : m_reserved)
        {
            value = start.ReadNtohU32();
        }
        return GetSerializedSize();
    }

    void Print(std::ostream& os) const override
    {
        os << "device=" << m_deviceId << " sampleNs=" << m_sampleTimeNs << " pos=("
           << m_position[0] << ',' << m_position[1] << ',' << m_position[2] << ')';
    }

    void Set(const Vector& position,
             const std::array<float, 4>& orientation,
             uint64_t sampleTimeNs,
             uint32_t deviceId)
    {
        m_position = {static_cast<float>(position.x),
                      static_cast<float>(position.y),
                      static_cast<float>(position.z)};
        m_orientation = orientation;
        m_sampleTimeNs = sampleTimeNs;
        m_deviceId = deviceId;
        m_reserved.fill(0);
    }

    const std::array<float, 3>& GetPosition() const
    {
        return m_position;
    }

    const std::array<float, 4>& GetOrientation() const
    {
        return m_orientation;
    }

    uint64_t GetSampleTimeNs() const
    {
        return m_sampleTimeNs;
    }

    uint32_t GetDeviceId() const
    {
        return m_deviceId;
    }

  private:
    std::array<float, 3> m_position{};
    // Quaternion order is (x, y, z, w).
    std::array<float, 4> m_orientation{};
    uint64_t m_sampleTimeNs{0};
    uint32_t m_deviceId{0};
    std::array<uint32_t, 5> m_reserved{};
};

class PoseReportHeader : public Header
{
  public:
    static TypeId GetTypeId()
    {
        static TypeId tid = TypeId("PoseReportHeader")
                                .SetParent<Header>()
                                .AddConstructor<PoseReportHeader>();
        return tid;
    }

    TypeId GetInstanceTypeId() const override
    {
        return GetTypeId();
    }

    uint32_t GetSerializedSize() const override
    {
        return REPORT_HEADER_BYTES;
    }

    void Serialize(Buffer::Iterator start) const override
    {
        start.WriteHtonU32(m_sequence);
        start.WriteHtonU64(m_sendTimeNs);
    }

    uint32_t Deserialize(Buffer::Iterator start) override
    {
        m_sequence = start.ReadNtohU32();
        m_sendTimeNs = start.ReadNtohU64();
        return GetSerializedSize();
    }

    void Print(std::ostream& os) const override
    {
        os << "seq=" << m_sequence << " sendNs=" << m_sendTimeNs;
    }

    void Set(uint32_t sequence, uint64_t sendTimeNs)
    {
        m_sequence = sequence;
        m_sendTimeNs = sendTimeNs;
    }

    uint32_t GetSequence() const
    {
        return m_sequence;
    }

    uint64_t GetSendTimeNs() const
    {
        return m_sendTimeNs;
    }

  private:
    uint32_t m_sequence{0};
    uint64_t m_sendTimeNs{0};
};

struct TxRecord
{
    uint32_t sequence;
    uint64_t sendTimeNs;
};

struct RxRecord
{
    uint32_t sequence;
    uint32_t deviceId;
    uint64_t sampleTimeNs;
    uint64_t sendTimeNs;
    uint64_t receiveTimeNs;
    uint32_t applicationBytes;
    std::array<float, 3> position;
    std::array<float, 4> orientation;
};

class PoseSource : public Application
{
  public:
    void Configure(Address peer,
                   Time duration,
                   Time sampleInterval,
                   uint32_t samplesPerReport,
                   Ptr<ConstantPositionMobilityModel> mobility)
    {
        m_peer = peer;
        m_duration = duration;
        m_sampleInterval = sampleInterval;
        m_samplesPerReport = samplesPerReport;
        m_mobility = mobility;
    }

    const std::vector<TxRecord>& GetRecords() const
    {
        return m_records;
    }

  private:
    void StartApplication() override
    {
        m_socket = Socket::CreateSocket(GetNode(), UdpSocketFactory::GetTypeId());
        NS_ABORT_MSG_IF(m_socket->Connect(m_peer) < 0, "Could not connect UDP source socket");
        m_totalSamples = static_cast<uint64_t>(m_duration.GetNanoSeconds() /
                                               m_sampleInterval.GetNanoSeconds());
        m_sampleEvent = Simulator::ScheduleNow(&PoseSource::SampleAndMaybeSend, this);
    }

    void StopApplication() override
    {
        Simulator::Cancel(m_sampleEvent);
        if (m_socket)
        {
            m_socket->Close();
        }
    }

    void SampleAndMaybeSend()
    {
        // A2 isolates the traffic model: pose values are fixed while every sample
        // receives a new timestamp. Quaternion order is (x, y, z, w).
        const Vector position = m_mobility->GetPosition();
        const std::array<float, 4> orientation = {0.0F, 0.0F, 0.0F, 1.0F};
        m_latestPose.Set(position,
                         orientation,
                         static_cast<uint64_t>(Simulator::Now().GetNanoSeconds()),
                         1);

        // Sampling and reporting occur in this function, so the current 1 ms sample is
        // unambiguously the one sent on each 10 ms report boundary.
        if ((m_sampleIndex % m_samplesPerReport) == 0)
        {
            SendLatestPose();
        }

        ++m_sampleIndex;
        if (m_sampleIndex < m_totalSamples)
        {
            m_sampleEvent =
                Simulator::Schedule(m_sampleInterval, &PoseSource::SampleAndMaybeSend, this);
        }
    }

    void SendLatestPose()
    {
        const uint64_t sendTimeNs = static_cast<uint64_t>(Simulator::Now().GetNanoSeconds());
        PoseReportHeader report;
        report.Set(m_sequence, sendTimeNs);

        Ptr<Packet> packet = Create<Packet>();
        packet->AddHeader(m_latestPose);
        packet->AddHeader(report);
        NS_ABORT_MSG_UNLESS(packet->GetSize() == POSE_BYTES + REPORT_HEADER_BYTES,
                            "Unexpected application packet size");

        const int bytesSent = m_socket->Send(packet);
        NS_ABORT_MSG_UNLESS(bytesSent == static_cast<int>(packet->GetSize()),
                            "UDP send failed");
        m_records.push_back({m_sequence, sendTimeNs});
        ++m_sequence;
    }

    Address m_peer;
    Time m_duration;
    Time m_sampleInterval;
    uint32_t m_samplesPerReport{10};
    uint64_t m_totalSamples{0};
    uint64_t m_sampleIndex{0};
    uint32_t m_sequence{0};
    EventId m_sampleEvent;
    Ptr<Socket> m_socket;
    Ptr<ConstantPositionMobilityModel> m_mobility;
    PosePayloadHeader m_latestPose;
    std::vector<TxRecord> m_records;
};

class PoseSink : public Application
{
  public:
    void Configure(uint16_t port)
    {
        m_port = port;
    }

    const std::vector<RxRecord>& GetRecords() const
    {
        return m_records;
    }

  private:
    void StartApplication() override
    {
        m_socket = Socket::CreateSocket(GetNode(), UdpSocketFactory::GetTypeId());
        NS_ABORT_MSG_IF(m_socket->Bind(InetSocketAddress(Ipv4Address::GetAny(), m_port)) < 0,
                        "Could not bind UDP sink socket");
        m_socket->SetRecvCallback(MakeCallback(&PoseSink::Receive, this));
    }

    void StopApplication() override
    {
        if (m_socket)
        {
            m_socket->SetRecvCallback(MakeNullCallback<void, Ptr<Socket>>());
            m_socket->Close();
        }
    }

    void Receive(Ptr<Socket> socket)
    {
        Address from;
        while (Ptr<Packet> packet = socket->RecvFrom(from))
        {
            const uint32_t applicationBytes = packet->GetSize();
            NS_ABORT_MSG_UNLESS(applicationBytes == POSE_BYTES + REPORT_HEADER_BYTES,
                                "Received an unexpected application packet size");

            PoseReportHeader report;
            PosePayloadHeader pose;
            NS_ABORT_MSG_UNLESS(packet->RemoveHeader(report) == REPORT_HEADER_BYTES,
                                "Could not decode report header");
            NS_ABORT_MSG_UNLESS(packet->RemoveHeader(pose) == POSE_BYTES,
                                "Could not decode pose payload");

            m_records.push_back({report.GetSequence(),
                                 pose.GetDeviceId(),
                                 pose.GetSampleTimeNs(),
                                 report.GetSendTimeNs(),
                                 static_cast<uint64_t>(Simulator::Now().GetNanoSeconds()),
                                 applicationBytes,
                                 pose.GetPosition(),
                                 pose.GetOrientation()});
        }
    }

    uint16_t m_port{5000};
    Ptr<Socket> m_socket;
    std::vector<RxRecord> m_records;
};

void
WriteOutputs(const std::string& prefix,
             const std::vector<TxRecord>& tx,
             const std::vector<RxRecord>& rx,
             double durationSeconds)
{
    std::ofstream packets(prefix + "-packets.csv");
    packets << "sequence,device_id,sample_time_ms,send_time_ms,receive_time_ms,"
               "delay_ms,pose_age_ms,application_bytes,ip_bytes,x,y,z,qx,qy,qz,qw\n";
    packets << std::fixed << std::setprecision(6);

    std::vector<double> delaysMs;
    std::vector<double> agesMs;
    delaysMs.reserve(rx.size());
    agesMs.reserve(rx.size());
    for (const auto& record : rx)
    {
        const double delay = (record.receiveTimeNs - record.sendTimeNs) / 1e6;
        const double age = (record.receiveTimeNs - record.sampleTimeNs) / 1e6;
        delaysMs.push_back(delay);
        agesMs.push_back(age);
        packets << record.sequence << ',' << record.deviceId << ',' << record.sampleTimeNs / 1e6
                << ',' << record.sendTimeNs / 1e6 << ',' << record.receiveTimeNs / 1e6 << ','
                << delay << ',' << age << ',' << record.applicationBytes << ',' << IP_PACKET_BYTES
                << ',' << record.position[0] << ',' << record.position[1] << ','
                << record.position[2] << ',' << record.orientation[0] << ','
                << record.orientation[1] << ',' << record.orientation[2] << ','
                << record.orientation[3] << '\n';
    }

    std::vector<double> intervalsMs;
    intervalsMs.reserve(tx.size() > 0 ? tx.size() - 1 : 0);
    for (std::size_t i = 1; i < tx.size(); ++i)
    {
        intervalsMs.push_back((tx[i].sendTimeNs - tx[i - 1].sendTimeNs) / 1e6);
    }

    auto average = [](const std::vector<double>& values) {
        return values.empty()
                   ? 0.0
                   : std::accumulate(values.begin(), values.end(), 0.0) / values.size();
    };
    const double maxDelay =
        delaysMs.empty() ? 0.0 : *std::max_element(delaysMs.begin(), delaysMs.end());
    const auto withinTarget =
        std::count_if(delaysMs.begin(), delaysMs.end(), [](double delay) { return delay <= 10.0; });
    const double withinTargetRatio =
        delaysMs.empty() ? 0.0 : static_cast<double>(withinTarget) / delaysMs.size();
    const double lossRate =
        tx.empty() ? 0.0 : static_cast<double>(tx.size() - rx.size()) / tx.size();

    std::ofstream summary(prefix + "-summary.csv");
    summary << "metric,value,unit\n" << std::fixed << std::setprecision(6);
    summary << "packets_sent," << tx.size() << ",packets\n";
    summary << "packets_received," << rx.size() << ",packets\n";
    summary << "packet_loss_rate," << lossRate << ",ratio\n";
    summary << "mean_delay," << average(delaysMs) << ",ms\n";
    summary << "max_delay," << maxDelay << ",ms\n";
    summary << "delay_within_10ms," << withinTargetRatio << ",ratio\n";
    summary << "mean_pose_age," << average(agesMs) << ",ms\n";
    summary << "mean_send_interval," << average(intervalsMs) << ",ms\n";
    summary << "ip_packet_size," << IP_PACKET_BYTES << ",bytes\n";
    summary << "offered_ip_rate," << (tx.size() * IP_PACKET_BYTES * 8.0 / durationSeconds)
            << ",bps\n";

    // These deterministic distributions each have one mass point. We still emit
    // explicit PMF (named PDF to match the assignment wording) and CDF files so
    // the generated traffic can be plotted and verified directly.
    std::ofstream sizePdf(prefix + "-size-pdf.csv");
    sizePdf << "ip_bytes,count,probability\n"
            << IP_PACKET_BYTES << ',' << tx.size() << ",1.0\n";
    std::ofstream sizeCdf(prefix + "-size-cdf.csv");
    sizeCdf << "ip_bytes,count,cdf\n" << IP_PACKET_BYTES << ',' << tx.size() << ",1.0\n";

    std::map<double, std::size_t> intervalCounts;
    for (double interval : intervalsMs)
    {
        ++intervalCounts[interval];
    }
    std::ofstream intervalPdf(prefix + "-interval-pdf.csv");
    intervalPdf << "send_interval_ms,count,probability\n" << std::fixed
                << std::setprecision(6);
    std::ofstream intervalCdf(prefix + "-interval-cdf.csv");
    intervalCdf << "send_interval_ms,count,cdf\n" << std::fixed << std::setprecision(6);
    std::size_t cumulative = 0;
    for (const auto& [interval, count] : intervalCounts)
    {
        cumulative += count;
        intervalPdf << interval << ',' << count << ','
                    << static_cast<double>(count) / intervalsMs.size() << '\n';
        intervalCdf << interval << ',' << count << ','
                    << static_cast<double>(cumulative) / intervalsMs.size() << '\n';
    }

    NS_LOG_UNCOND("Sent=" << tx.size() << " received=" << rx.size()
                           << " loss=" << lossRate * 100.0 << "%");
    NS_LOG_UNCOND("Delay mean=" << average(delaysMs) << " ms max=" << maxDelay
                                 << " ms <=10ms=" << withinTargetRatio * 100.0 << "%");
    NS_LOG_UNCOND("Pose age mean=" << average(agesMs) << " ms, IP offered rate="
                                    << tx.size() * IP_PACKET_BYTES * 8.0 / durationSeconds
                                    << " bps");
}

} // namespace

int
main(int argc, char* argv[])
{
    double durationSeconds = 60.0;
    std::string dataRate = "10Mbps";
    std::string channelDelay = "1ms";
    std::string outputPrefix = "xr-pose-uplink";
    bool enablePcap = true;

    CommandLine cmd(__FILE__);
    cmd.AddValue("duration", "Pose reporting duration in seconds", durationSeconds);
    cmd.AddValue("dataRate", "Point-to-point link rate", dataRate);
    cmd.AddValue("channelDelay", "Point-to-point one-way propagation delay", channelDelay);
    cmd.AddValue("outputPrefix", "Prefix for CSV and PCAP files", outputPrefix);
    cmd.AddValue("enablePcap", "Write point-to-point PCAP files", enablePcap);
    cmd.Parse(argc, argv);

    const Time sampleInterval = MilliSeconds(1);
    constexpr uint32_t samplesPerReport = 10;
    constexpr uint16_t port = 5000;
    const Time duration = Seconds(durationSeconds);
    NS_ABORT_MSG_IF(durationSeconds <= 0.0, "Duration must be positive");

    NodeContainer nodes;
    nodes.Create(2);

    PointToPointHelper pointToPoint;
    pointToPoint.SetDeviceAttribute("DataRate", StringValue(dataRate));
    pointToPoint.SetChannelAttribute("Delay", StringValue(channelDelay));
    pointToPoint.SetQueue("ns3::DropTailQueue", "MaxSize", StringValue("100p"));
    NetDeviceContainer devices = pointToPoint.Install(nodes);

    InternetStackHelper internet;
    internet.Install(nodes);
    Ipv4AddressHelper ipv4;
    ipv4.SetBase("10.1.1.0", "255.255.255.0");
    Ipv4InterfaceContainer interfaces = ipv4.Assign(devices);

    Ptr<ConstantPositionMobilityModel> sourceMobility =
        CreateObject<ConstantPositionMobilityModel>();
    sourceMobility->SetPosition(Vector(1.0, 1.0, 1.2));
    nodes.Get(0)->AggregateObject(sourceMobility);
    Ptr<ConstantPositionMobilityModel> sinkMobility =
        CreateObject<ConstantPositionMobilityModel>();
    sinkMobility->SetPosition(Vector(0.0, 0.0, 0.0));
    nodes.Get(1)->AggregateObject(sinkMobility);

    Ptr<PoseSink> sink = CreateObject<PoseSink>();
    sink->Configure(port);
    nodes.Get(1)->AddApplication(sink);
    sink->SetStartTime(Seconds(0.5));
    sink->SetStopTime(Seconds(1.0) + duration + MilliSeconds(100));

    Ptr<PoseSource> source = CreateObject<PoseSource>();
    source->Configure(InetSocketAddress(interfaces.GetAddress(1), port),
                      duration,
                      sampleInterval,
                      samplesPerReport,
                      sourceMobility);
    nodes.Get(0)->AddApplication(source);
    source->SetStartTime(Seconds(1.0));
    source->SetStopTime(Seconds(1.0) + duration + MilliSeconds(10));

    if (enablePcap)
    {
        // PCAP contains a 2-byte PPP header outside the 100-byte IPv4 packet.
        pointToPoint.EnablePcapAll(outputPrefix, true);
    }

    Simulator::Stop(Seconds(1.0) + duration + MilliSeconds(100));
    Simulator::Run();

    WriteOutputs(outputPrefix, source->GetRecords(), sink->GetRecords(), durationSeconds);
    Simulator::Destroy();
    return 0;
}
