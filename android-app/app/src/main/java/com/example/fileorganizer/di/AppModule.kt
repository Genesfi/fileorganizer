package com.example.fileorganizer.di

import android.content.Context
import androidx.room.Room
import com.example.fileorganizer.data.AppDatabase
import com.example.fileorganizer.data.HistoryDao
import com.example.fileorganizer.data.SettingsManager
import com.example.fileorganizer.data.TemplateManager
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object AppModule {

    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): AppDatabase {
        return Room.databaseBuilder(
            context,
            AppDatabase::class.java,
            "file_organizer_db"
        ).build()
    }

    @Provides
    fun provideHistoryDao(db: AppDatabase): HistoryDao {
        return db.historyDao()
    }

    @Provides
    @Singleton
    fun provideTemplateManager(): TemplateManager {
        return TemplateManager()
    }

    @Provides
    @Singleton
    fun provideSettingsManager(@ApplicationContext context: Context): SettingsManager {
        return SettingsManager(context)
    }
}
