"""Benchmark for Component class discovery caching optimization."""

import timeit
from pyagentspec.component import Component, _get_class_from_name_cached, _get_all_subclasses_cached


def benchmark_get_class_from_name():
    print("=== Benchmarking get_class_from_name() ===")
    
    Component.get_class_from_name("Agent")
    
    num_iterations = 1000
    
    def lookup_repeated():
        for _ in range(num_iterations):
            Component.get_class_from_name("Agent")
    
    time_taken = timeit.timeit(lookup_repeated, number=10)
    print(f"1000 repeated lookups x 10 runs: {time_taken:.4f}s")
    print(f"Average per lookup (with cache): {time_taken / (num_iterations * 10) * 1000:.4f}ms")
    print(f"Cache info: {_get_class_from_name_cached.cache_info()}")
    print()


def benchmark_get_all_subclasses():
    print("=== Benchmarking _get_all_subclasses() ===")
    
    Component._get_all_subclasses()
    
    num_iterations = 100
    
    def lookup_repeated():
        for _ in range(num_iterations):
            Component._get_all_subclasses()
    
    time_taken = timeit.timeit(lookup_repeated, number=10)
    print(f"100 repeated calls x 10 runs: {time_taken:.4f}s")
    print(f"Average per call (with cache): {time_taken / (num_iterations * 10) * 1000:.4f}ms")
    print(f"Cache info: {_get_all_subclasses_cached.cache_info()}")
    print()


def benchmark_multiple_classes():
    print("=== Benchmarking multiple class lookups ===")
    
    class_names = ["Agent", "Flow", "LLMConfig", "LlmNode", "StartNode", "EndNode"]
    
    for name in class_names:
        Component.get_class_from_name(name)
    
    def lookup_multiple():
        for _ in range(100):
            for name in class_names:
                Component.get_class_from_name(name)
    
    time_taken = timeit.timeit(lookup_multiple, number=10)
    total_lookups = 100 * len(class_names) * 10
    print(f"100 iterations x {len(class_names)} classes x 10 runs: {time_taken:.4f}s")
    print(f"Average per lookup (cached): {time_taken / total_lookups * 1000:.4f}ms")
    print(f"Cache info: {_get_class_from_name_cached.cache_info()}")
    print()


def benchmark_simulated_deserialization():
    print("=== Benchmarking simulated deserialization workload ===")
    
    workload = [
        "Agent", "Flow", "Agent", "LLMConfig", 
        "LlmNode", "StartNode", "EndNode", "LlmNode",
        "Agent", "Flow", "LLMConfig", "Agent"
    ]
    
    def simulated_workload():
        for x in range(50):
            for class_name in workload:
                Component.get_class_from_name(class_name)
                Component._get_all_subclasses()
    
    time_taken = timeit.timeit(simulated_workload, number=5)
    print(f"Simulated deserialization (50 components x {len(workload)} lookups x 5 runs): {time_taken:.4f}s")
    print(f"Cache info (get_class_from_name): {_get_class_from_name_cached.cache_info()}")
    print(f"Cache info (_get_all_subclasses): {_get_all_subclasses_cached.cache_info()}")
    print()


if __name__ == "__main__":
    print("Component Class Discovery Caching Benchmark")
    print("=" * 50)
    print()
    
    benchmark_get_class_from_name()
    benchmark_get_all_subclasses()
    benchmark_multiple_classes()
    benchmark_simulated_deserialization()
    
    print("Benchmark complete!")
    print()
    print("Note: Without caching, each lookup traverses the class hierarchy")
    print("via BFS. With caching, repeated lookups are O(1) dict lookups.")
