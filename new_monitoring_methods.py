    def _run_monitoring(self):
        """Основной цикл мониторинга с правильной логикой"""
        print(f"{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}{Style.BRIGHT}📊 МОНИТОРИНГ СИСТЕМЫ")
        print(f"{Fore.CYAN}{'='*80}\n")
        
        while self.running:
            try:
                # 1. Показываем статус системы
                self._display_system_status()
                
                # 2. Проверяем необработанные интервью
                unprocessed_count = self._get_unprocessed_count()
                unprocessed_details = self._get_unprocessed_details()
                
                if unprocessed_count > 0:
                    print(f"\n{Fore.YELLOW}🔄 Найдено {unprocessed_count} необработанных интервью. Начинаем обработку...")
                    
                    # 3. Обрабатываем кандидатов с показом прогресса
                    self._process_candidates_with_progress(unprocessed_details)
                    
                    # 4. Показываем статус после обработки
                    print(f"\n{Fore.GREEN}✅ Обработка завершена!")
                    self._display_system_status()
                else:
                    print(f"\n{Fore.GREEN}✅ Все интервью обработаны. Очередь пуста.")
                
                # 5. Ждем 1 минуту до следующей проверки
                print(f"\n{Fore.BLUE}⏰ Следующая проверка через 1 минуту...")
                self._countdown_wait(60)
                
            except requests.exceptions.RequestException:
                if self.running:
                    print(f"{Fore.RED}⚠️  Потеряна связь с сервером. Повтор через 30 секунд...")
                    self._countdown_wait(30)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"{Fore.RED}❌ Ошибка мониторинга: {e}")
                self._countdown_wait(30)
    
    def _display_system_status(self):
        """Отображение статуса системы"""
        try:
            # Получение статуса системы
            system_status = self._get_system_status()
            task_status = self._get_task_status()
            unprocessed_count = self._get_unprocessed_count()
            current_time = datetime.now().strftime('%H:%M:%S')
            
            print(f"\n{Fore.CYAN}{'─'*60}")
            print(f"{Fore.CYAN}⏰ Статус системы: {current_time}")
            print(f"{Fore.CYAN}{'─'*60}")
            
            # Система
            if system_status and system_status.get('success'):
                print(f"🖥️  Система: {Fore.GREEN}Работает нормально")
            else:
                print(f"🖥️  Система: {Fore.RED}Недоступна")
            
            # Планировщик
            if task_status and task_status.get('success'):
                status_data = task_status.get('status', {})
                scheduler_status = status_data.get('scheduler_status', 'unknown')
                auto_processing = task_status.get('auto_processing_enabled', False)
                
                if scheduler_status == 'running':
                    scheduler_icon = "✅"
                    scheduler_text = "Работает"
                elif scheduler_status == 'stopped':
                    scheduler_icon = "⏸️"
                    scheduler_text = "Остановлен"
                else:
                    scheduler_icon = "❌"
                    scheduler_text = "Неинициализирован"
                
                print(f"⚙️  Планировщик: {scheduler_icon} {scheduler_text}")
                
                auto_icon = "✅" if auto_processing else "❌"
                auto_text = "Включена" if auto_processing else "Выключена"
                print(f"🔄 Автообработка: {auto_icon} {auto_text}")
            else:
                print(f"⚙️  Планировщик: {Fore.RED}Недоступен")
            
            # Очередь
            print(f"📋 Очередь: ", end="")
            if unprocessed_count > 0:
                print(f"{Fore.YELLOW}{unprocessed_count} интервью ожидают обработки")
            else:
                print(f"{Fore.GREEN}Пуста")
            
            print(f"{Fore.CYAN}{'─'*60}")
            
        except Exception as e:
            print(f"{Fore.RED}❌ Ошибка получения статуса: {e}")
    
    def _process_candidates_with_progress(self, candidates):
        """Обработка кандидатов с показом прогресса"""
        if not candidates:
            return
        
        total = len(candidates)
        print(f"\n{Fore.CYAN}📊 Прогресс обработки:")
        print(f"{Fore.CYAN}{'─'*40}")
        
        for i, candidate in enumerate(candidates, 1):
            name = candidate.get('name', 'Неизвестно')
            candidate_id = candidate.get('id', 'N/A')
            
            print(f"{Fore.YELLOW}⏳ [{i}/{total}] Обрабатывается: {name} (ID: {candidate_id})")
            
            # Запускаем обработку через API
            try:
                response = requests.post(f"{self.api_url}/api/v1/tasks/process/{candidate_id}", timeout=300)
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        print(f"{Fore.GREEN}✅ [{i}/{total}] Готово: {name}")
                    else:
                        print(f"{Fore.RED}❌ [{i}/{total}] Ошибка: {name} - {result.get('error', 'Неизвестная ошибка')}")
                else:
                    print(f"{Fore.RED}❌ [{i}/{total}] HTTP ошибка: {name} - {response.status_code}")
                    
            except requests.exceptions.Timeout:
                print(f"{Fore.RED}❌ [{i}/{total}] Таймаут: {name}")
            except Exception as e:
                print(f"{Fore.RED}❌ [{i}/{total}] Исключение: {name} - {str(e)}")
        
        print(f"{Fore.CYAN}{'─'*40}")
        print(f"{Fore.GREEN}📊 Обработка завершена: {total} интервью")
    
    def _countdown_wait(self, seconds):
        """Обратный отсчет с возможностью прерывания"""
        print(f"{Fore.BLUE}⏳ Ожидание {seconds} секунд (Ctrl+C для остановки)...")
        
        for remaining in range(seconds, 0, -1):
            if not self.running:
                break
            
            if remaining % 10 == 0 or remaining <= 5:
                print(f"{Fore.BLUE}⏳ Осталось: {remaining} сек", end="\r")
            
            time.sleep(1)
        
        if self.running:
            print(f"{Fore.BLUE}⏳ Ожидание завершено." + " " * 20)