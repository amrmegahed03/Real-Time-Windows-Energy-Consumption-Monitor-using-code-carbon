from time import perf_counter
import psutil
import time
from codecarbon.external.hardware import CPU, GPU, RAM, AppleSiliconChip
from codecarbon.external.logger import logger


class MeasurePowerEnergy:
    """
    Measure power and energy consumption of a hardware component.
    """
    disk_base_watts = None
    network_base_watts = None
    peripherals_base_watts = None

    _last_measured_time: int = 0
    _hardware: list
    _pue: float
    _total_cpu_energy: float
    _total_gpu_energy: float
    _total_ram_energy: float
    _total_energy: float
    _cpu_power: float
    _gpu_power: float
    _ram_power: float

    def __init__(self, hardware, pue, disk_power=10, network_power=3, peripheral_power=10):
        """
        :param hardware: list of hardware components to measure
        :param pue: Power Usage Effectiveness of the datacenter
        """

        self._last_measured_time = perf_counter()
        self._hardware = hardware
        self._pue = pue

        self.disk_base_watts = disk_power
        self.network_base_watts = network_power
        self.peripherals_base_watts = peripheral_power


        # TODO: Read initial energy values from hardware
        self._total_cpu_energy = 0
        self._total_gpu_energy = 0
        self._total_ram_energy = 0
        self._total_energy = 0
        # Power cant't be read at init because we need time, so we set it to 0
        self._cpu_power = 0
        self._gpu_power = 0
        self._ram_power = 0
        self._system_power = 0
        self.system_energy = 0

    def get_estimated_system_power(self):
        """
        Estimate system power excluding CPU and RAM.
        Includes approximated disk, network, and peripherals draw.
        """
        # === Base power assumptions ===
        """
        disk_base_watts = 10                  # Your SSDs: ~6W + ~4W
        network_max_bytes = 125_000_000       # ~1 Gbps = 125MB/s
        network_base_watts = 3                # Assumed draw at full bandwidth
        peripherals_base_watts = 10           # Estimate for USB, audio, etc.
        """
        disk_base_watts = self.disk_base_watts
        network_base_watts = self.network_base_watts
        peripherals_base_watts = self.peripherals_base_watts
        network_max_bytes = 125_000_000  # ~1 Gbps = 125MB/s

        # === Disk usage ===
        disk1 = psutil.disk_io_counters()
        time.sleep(1)  # Measure over 1 second
        disk2 = psutil.disk_io_counters()
        bytes_read = disk2.read_bytes - disk1.read_bytes
        bytes_written = disk2.write_bytes - disk1.write_bytes
        total_bytes = bytes_read + bytes_written
        disk_usage_ratio = min(total_bytes / network_max_bytes, 1.0)
        disk_power = disk_usage_ratio * disk_base_watts
        # disk_power = disk_base_watts  # Uncomment if you want to use the base power directly
        # disk_power = 0  # Uncomment if you want to ignore disk power

        # === Network usage ===
        net1 = psutil.net_io_counters()
        time.sleep(1)  # Measure over 1 second
        net2 = psutil.net_io_counters()
        bytes_sent = net2.bytes_sent - net1.bytes_sent
        bytes_recv = net2.bytes_recv - net1.bytes_recv
        total_bytes = bytes_sent + bytes_recv
        net_usage_ratio = min(total_bytes / network_max_bytes, 1.0)
        network_power = net_usage_ratio * network_base_watts

        # === Combine all estimates ===
        self._system_power = disk_power + network_power + peripherals_base_watts
        return self._system_power

  

    def do_measure(self) -> None:
        for hardware in self._hardware:
            h_time = perf_counter()
            # Compute last_duration again for more accuracy
            last_duration = perf_counter() - self._last_measured_time
            power, energy = hardware.measure_power_and_energy(
                last_duration=last_duration
            )
            # Apply the PUE of the datacenter to the consumed energy
            energy *= self._pue
            self._total_energy += energy
            if isinstance(hardware, CPU):
                # Estimate power from CPU usage using psutil
                cpu_percent = psutil.cpu_percent(interval=None)
                cpu_base_watts = 65  # Approximate TDP for your i7-10750H

                estimated_cpu_power = (cpu_percent / 100) * cpu_base_watts
                power.W = estimated_cpu_power  # Override power reading

                self._total_cpu_energy += energy
                self._cpu_power = power

                logger.info(
                    f"Energy consumed for all CPUs : {self._total_cpu_energy.kWh:.6f} kWh"
                    + f". Estimated CPU Power : {self._cpu_power.W:.2f} W"
                )
            elif isinstance(hardware, GPU):
                self._total_gpu_energy += energy
                self._gpu_power = power
                logger.info(
                    f"Energy consumed for all GPUs : {self._total_gpu_energy.kWh:.6f} kWh"
                    + f". Total GPU Power : {self._gpu_power.W} W"
                )
            elif isinstance(hardware, RAM):
                self._total_ram_energy += energy
                self._ram_power = power
                logger.info(
                    f"Energy consumed for RAM : {self._total_ram_energy.kWh:.6f} kWh."
                    + f"RAM Power : {self._ram_power.W} W"
                )
            elif isinstance(hardware, AppleSiliconChip):
                if hardware.chip_part == "CPU":
                    self._total_cpu_energy += energy
                    self._cpu_power = power
                    logger.info(
                        f"Energy consumed for AppleSilicon CPU : {self._total_cpu_energy.kWh:.6f} kWh"
                        + f".Apple Silicon CPU Power : {self._cpu_power.W} W"
                    )
                elif hardware.chip_part == "GPU":
                    self._total_gpu_energy += energy
                    self._gpu_power = power
                    logger.info(
                        f"Energy consumed for AppleSilicon GPU : {self._total_gpu_energy.kWh:.6f} kWh"
                        + f".Apple Silicon GPU Power : {self._gpu_power.W} W"
                    )
            else:
                logger.error(f"Unknown hardware type: {hardware} ({type(hardware)})")
            h_time = perf_counter() - h_time
            logger.debug(
                f"{hardware.__class__.__name__} : {hardware.total_power().W:,.2f} "
                + f"W during {last_duration:,.2f} s [measurement time: {h_time:,.4f}]"
            )
        self._system_power = self.get_estimated_system_power()
        last_duration = perf_counter() - self._last_measured_time

        self.system_energy += (self._system_power * last_duration) / 3600  

        logger.info(f"Estimated Total System Power (software-based): {self._system_power:.2f} W")
        logger.info(f"Estimated System Energy (software-based): {self.system_energy:.6f} kWh")

        logger.info(
            f"{self._total_energy.kWh:.6f} kWh of electricity used since the beginning."
        )
        self._last_measured_time = perf_counter()  


   