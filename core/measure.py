from time import perf_counter
import psutil
from codecarbon.external.hardware import CPU, GPU, RAM, AppleSiliconChip
from codecarbon.external.logger import logger


class MeasurePowerEnergy:
    """
    Measure power and energy consumption of a hardware component.
    """

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

    def __init__(self, hardware, pue):
        """
        :param hardware: list of hardware components to measure
        :param pue: Power Usage Effectiveness of the datacenter
        """
        self._last_measured_time = perf_counter()
        self._hardware = hardware
        self._pue = pue
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

    def get_estimated_system_power(self):
        """
        Estimate full system power draw using CPU, RAM, and disk usage.
        These are approximations — for real measurements, a smart plug is needed.
        """
        cpu_percent = psutil.cpu_percent(interval=1)
        ram_percent = psutil.virtual_memory().percent
        disk_percent = psutil.disk_usage('/').percent

        # Base assumptions (can be fine-tuned)
        cpu_base_watts = 65      # Typical CPU TDP
        ram_base_watts = 8       # Approximate full RAM draw
        disk_base_watts = 5      # Average SSD/HDD draw

        self._system_power = (
            (cpu_percent / 100) * cpu_base_watts +
            (ram_percent / 100) * ram_base_watts +
            (disk_percent / 100) * disk_base_watts
        )

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
                self._total_cpu_energy += energy
                self._cpu_power = power
                logger.info(
                    f"Energy consumed for all CPUs : {self._total_cpu_energy.kWh:.6f} kWh"
                    + f". Total CPU Power : {self._cpu_power.W} W"
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
        logger.info(f"Estimated Total System Power (software-based): {self._system_power:.2f} W")

        logger.info(
            f"{self._total_energy.kWh:.6f} kWh of electricity used since the beginning."
        )

   